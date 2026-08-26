"""
rag.py — The RAGPipeline class: wires ingestion, embedding, storage, and generation.

LEARNING NOTE — Why a class instead of functions?
  The Embedder loads a ~90MB model on instantiation. If we used functions,
  we'd reload it on every request (3 seconds each time).
  
  By wrapping everything in a class, we load once at startup and reuse
  the same objects for every request. This is the Singleton pattern —
  one instance serves all requests.

LEARNING NOTE — The generate() method uses "grounding":
  The system prompt tells the LLM to ONLY answer from the provided context.
  If the context doesn't contain the answer, it must say "I don't know".
  This is fundamentally different from asking the LLM a direct question —
  it cannot use its training data to fill in gaps.
  
  Without this, the LLM would happily make up a plausible-sounding answer
  even when the document says nothing about the topic.
"""

from google import genai
from app.pipeline.ingestion import DocumentChunker
from app.pipeline.embedder import Embedder
from app.pipeline.store import VectorStore
from app.config import settings
from app.utils.logger import get_logger, Timer

logger = get_logger(__name__)


class RAGPipeline:
    """
    The main pipeline class. Exposes two public methods:
      - ingest(file_path): load a document into the vector store
      - query(question):   answer a question using retrieved context
    """

    def __init__(self):
        # All three are loaded once here — expensive initialisation happens once,
        # not on every API request.
        self.chunker = DocumentChunker()
        self.embedder = Embedder()
        self.store = VectorStore()

        # Configure the Gemini client once at startup.
        # genai.configure() sets the API key globally for all subsequent calls.
        # GenerativeModel() is lightweight — it doesn't make a network call here.
        self.llm = genai.Client(api_key=settings.gemini_api_key)
        self.system_instruction = """You are a precise question-answering assistant.

            RULES — you must follow all of these:
            1. Answer ONLY using the provided context. Do not use any external knowledge.
            2. If the context doesn't contain enough information, say "The provided document doesn't cover this topic."
            3. Be concise and direct. No padding or filler phrases.
            4. Do not make up details, statistics, or facts not present in the context."""
        
        logger.info(
            "RAGPipeline initialised",
            extra={"extra": {"model": settings.gemini_model}}
        )

    # ──────────────────────────────────────────────────────────────────────────
    # INGESTION
    # ──────────────────────────────────────────────────────────────────────────

    def ingest(self, file_path: str) -> dict:
        """
        Load a document, chunk it, embed the chunks, and store them.
        
        Full pipeline:
          file_path → load text → split into chunks → embed → store in ChromaDB
        
        Args:
            file_path: Path to a .txt or .md file.
        
        Returns:
            {"chunks_stored": int, "file": str}
        """
        with Timer() as t:
            # Step 1: Load and chunk
            logger.info("Starting ingestion", extra={"extra": {"file": file_path}})
            chunks = self.chunker.load_and_chunk(file_path)

            # Step 2: Embed all chunks (batch operation — fast)
            chunk_texts = [c["text"] for c in chunks]
            embeddings = self.embedder.embed(chunk_texts)

            # Step 3: Store in ChromaDB
            self.store.add(chunks, embeddings)

        logger.info(
            "Ingestion complete",
            extra={"extra": {
                "file": file_path,
                "chunks_stored": len(chunks),
                "latency_ms": t.elapsed_ms,
            }}
        )
        return {"chunks_stored": len(chunks), "file": file_path}

    # ──────────────────────────────────────────────────────────────────────────
    # QUERY
    # ──────────────────────────────────────────────────────────────────────────

    def query(self, question: str, top_k: int = settings.top_k) -> dict:
        """
        Answer a question using retrieved document context.
        
        Full pipeline:
          question → embed → retrieve top-k chunks → check relevance →
          build prompt → generate → return answer + sources
        
        Args:
            question: The user's question.
            top_k:    How many chunks to retrieve (default from settings).
        
        Returns:
            {
              "answer": str,
              "sources": list[str],
              "similarity_scores": list[float],
              "grounded": bool  ← False if no relevant chunks found
            }
        """
        with Timer() as t:
            # Step 1: Embed the question using the same model as the chunks
            # (CRITICAL: must use the same embedding model for comparison to work)
            query_embedding = self.embedder.embed_one(question)

            # Step 2: Retrieve top-k most similar chunks from ChromaDB
            results = self.store.query(query_embedding, top_k=top_k)
            retrieved_texts = results["documents"][0]       # list of chunk texts
            distances = results["distances"][0]             # list of cosine distances

            # Step 3: Relevance check
            # ChromaDB returns DISTANCE (0=identical, 1=completely different)
            # If the closest chunk is still too far, the document doesn't cover this topic
            if not retrieved_texts or distances[0] > settings.relevance_threshold:
                logger.info(
                    "No relevant chunks found",
                    extra={"extra": {
                        "question": question,
                        "closest_distance": distances[0] if distances else None,
                        "threshold": settings.relevance_threshold,
                    }}
                )
                return {
                    "answer": "I don't have information about this in the provided document.",
                    "sources": [],
                    "similarity_scores": [],
                    "grounded": False,
                }

            # Step 4: Filter to only chunks below the relevance threshold
            relevant_pairs = [
                (text, dist)
                for text, dist in zip(retrieved_texts, distances)
                if dist <= settings.relevance_threshold
            ]
            relevant_texts = [p[0] for p in relevant_pairs]
            relevant_scores = [round(1 - p[1], 3) for p in relevant_pairs]
            # Convert distance → similarity: similarity = 1 - distance
            # distance 0.12 → similarity 0.88  (88% similar)
            # distance 0.50 → similarity 0.50  (50% similar, our cutoff)

            # Step 5: Build augmented prompt
            context = "\n\n---\n\n".join(relevant_texts)

            # Step 6: Generate answer (grounded in context only)
            answer = self._generate(question, context)

        logger.info(
            "Query complete",
            extra={"extra": {
                "question": question,
                "chunks_used": len(relevant_texts),
                "top_similarity": relevant_scores[0] if relevant_scores else 0,
                "latency_ms": t.elapsed_ms,
            }}
        )

        return {
            "answer": answer,
            "sources": relevant_texts,
            "similarity_scores": relevant_scores,
            "grounded": True,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # PRIVATE: LLM GENERATION
    # ──────────────────────────────────────────────────────────────────────────

    def _generate(self, question: str, context: str) -> str:
        prompt = f"""Context from the document:
    {context}

    Question: {question}

    Answer using only the context above:"""

        response = self.llm.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config={
                "system_instruction": self.system_instruction,
            }
        )

        # Handle both streaming and non-streaming responses
        if hasattr(response, "text"):
            return response.text
        
        # If it's a generator, collect all chunks
        full_text = ""
        for chunk in response:
            if hasattr(chunk, "text"):
                full_text += chunk.text
        return full_text
