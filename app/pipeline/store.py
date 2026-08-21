"""
store.py — ChromaDB vector store: add chunks, query by similarity.

LEARNING NOTE — What is ChromaDB?
  ChromaDB is a vector database. It stores:
    1. The embedding vector (for similarity search)
    2. The original text (to return as the source)
    3. Optional metadata (filename, chunk index, etc.)
  
  At query time, you give it a query vector and it returns the
  most similar stored vectors — using cosine distance.
  
  ChromaDB options:
    - chromadb.Client()               → in-memory (lost on restart)
    - chromadb.PersistentClient(path) → saved to disk (survives restarts) ← we use this
    - chromadb.HttpClient(host=...)   → connects to a ChromaDB server

LEARNING NOTE — ChromaDB distance scores:
  ChromaDB returns DISTANCE (not similarity).
  Distance 0.0 = vectors are identical.
  Distance 1.0 = vectors are completely different (for cosine).
  
  So when checking relevance:
    distance < threshold → RELEVANT   (close to query)
    distance > threshold → NOT RELEVANT (far from query)
  
  This is the OPPOSITE of what you might expect if you're thinking
  in terms of "similarity score". Don't confuse the two!
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "documents"


class VectorStore:
    def __init__(self):
        # PersistentClient saves to disk — survives API restarts
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),  # disable telemetry
        )
        # get_or_create: safe to call on every startup
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            # "cosine" distance = direction-based similarity (length-independent)
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "VectorStore ready",
            extra={"extra": {"collection": COLLECTION_NAME, "chunks": self.count()}}
        )

    def add(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        """
        Add chunks and their embeddings to ChromaDB.
        
        Args:
            chunks:     List of chunk dicts from DocumentChunker (must have 'id' and 'text')
            embeddings: Parallel list of embedding vectors from Embedder
        """
        if not chunks:
            return

        self.collection.add(
            ids=[c["id"] for c in chunks],           # unique string IDs
            documents=[c["text"] for c in chunks],    # original text (returned at query time)
            embeddings=embeddings,                    # vectors (used for similarity search)
            metadatas=[{                              # any extra info to store
                "token_count": c["token_count"],
                "start_token": c["start_token"],
            } for c in chunks],
        )
        logger.info(
            "Chunks added to store",
            extra={"extra": {"added": len(chunks), "total": self.count()}}
        )

    def query(self, query_embedding: list[float], top_k: int = settings.top_k) -> dict:
        """
        Find the top_k most similar chunks to the query embedding.
        
        Returns:
            {
              "documents": [["chunk text 1", "chunk text 2", ...]],
              "distances": [[0.12, 0.34, ...]],   ← lower = more similar
            }
        
        Note: ChromaDB wraps results in an extra list (batch interface),
        so we access results["documents"][0], not results["documents"].
        """
        if self.count() == 0:
            return {"documents": [[]], "distances": [[]]}

        results = self.collection.query(
            query_embeddings=[query_embedding],  # wrapped in list (batch interface)
            n_results=min(top_k, self.count()),  # can't request more than what exists
        )
        return results

    def count(self) -> int:
        """Return the number of chunks stored."""
        return self.collection.count()

    def clear(self) -> None:
        """Delete and recreate the collection (start fresh)."""
        self.client.delete_collection(COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Collection cleared")
