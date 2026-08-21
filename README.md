# RAG Question-Answering API

> Ingest any document. Ask questions. Get answers grounded **only** in that document — with sources and similarity scores.

---

## What It Does

Upload a text document, then ask questions about it via a REST API. The system retrieves the most relevant chunks from your document, passes them as context to an LLM, and returns the answer alongside the exact source passages it used. If your question isn't covered by the document, it says so — it does **not** hallucinate.

---

## Architecture

```
INGESTION (once per document)
─────────────────────────────
  .txt file
      │
      ▼
  DocumentChunker          ← splits into 512-token chunks, 50-token overlap
      │
      ▼
  Embedder                 ← sentence-transformers (all-MiniLM-L6-v2)
      │
      ▼
  ChromaDB                 ← stores vectors + original text locally


QUERY (per user question)
─────────────────────────
  User question
      │
      ▼
  Embedder                 ← embed the question into a vector
      │
      ▼
  ChromaDB similarity search  ← cosine distance, retrieve top-k chunks
      │
      ▼
  Relevance check          ← if score < threshold → "I don't have info on this"
      │
      ▼
  Prompt augmentation      ← insert retrieved chunks as context
      │
      ▼
  Anthropic API            ← generate answer using ONLY the context
      │
      ▼
  Response: { answer, sources, similarity_scores, grounded }
```

---

## Tech Stack

| Tool | Why |
|---|---|
| **FastAPI** | Auto-generates OpenAPI docs, Pydantic validation, async support |
| **ChromaDB** | Local vector database — no server, no cloud account needed |
| **sentence-transformers** | `all-MiniLM-L6-v2` — fast, accurate, free embeddings |
| **tiktoken** | OpenAI's tokenizer — accurate token counting for chunking |
| **Anthropic API** | LLM for answer generation |
| **Docker** | Consistent environment — works the same everywhere |
| **pytest** | Unit tests for core pipeline logic |

---

## Project Structure

```
rag-qa-api/
├── app/
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # All settings (loaded from .env)
│   ├── pipeline/
│   │   ├── ingestion.py      # Load file → split into chunks
│   │   ├── embedder.py       # Text → vectors (sentence-transformers)
│   │   ├── store.py          # ChromaDB read/write operations
│   │   └── rag.py            # RAGPipeline: wires everything together
│   ├── api/
│   │   ├── models.py         # Pydantic request/response schemas
│   │   └── routes.py         # FastAPI route handlers
│   └── utils/
│       └── logger.py         # Structured JSON logging
├── tests/
│   └── test_pipeline.py      # Unit tests with pytest
├── sample_docs/
│   └── ml_basics.txt         # Sample document to test with
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/rag-qa-api
cd rag-qa-api
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

### 3. Run locally

```bash
uvicorn app.main:app --reload
# API docs: http://localhost:8000/docs
```

### 4. Run with Docker

```bash
docker build -t rag-api .
docker run -p 8000:8000 --env-file .env rag-api
```

---

## API Endpoints

### `GET /v1/health`
Check the API is running.

```bash
curl http://localhost:8000/v1/health
# {"status": "ok", "chunks_stored": 24}
```

### `POST /v1/ingest`
Load a document into the vector store.

```bash
curl -X POST http://localhost:8000/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"file_path": "sample_docs/ml_basics.txt"}'

# {"message": "Ingested successfully", "chunks_stored": 24, "file": "ml_basics.txt"}
```

### `POST /v1/query`
Ask a question about the ingested document.

```bash
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is overfitting?", "top_k": 3}'

# {
#   "answer": "Overfitting occurs when a model learns...",
#   "sources": ["Overfitting happens when the model...", "..."],
#   "similarity_scores": [0.82, 0.74, 0.61],
#   "grounded": true
# }
```

### `DELETE /v1/collection`
Clear the vector store and start fresh.

```bash
curl -X DELETE http://localhost:8000/v1/collection
# {"message": "Collection cleared"}
```

---

## Example Output

**Relevant question:**
```json
{
  "answer": "Overfitting occurs when a model performs well on training data but poorly on unseen data. It happens when the model is too complex and memorises the training examples including their noise, rather than learning general patterns.",
  "sources": [
    "Overfitting happens when the model learns the training data too well, including noise and outliers...",
    "To detect overfitting, compare training accuracy to validation accuracy. A large gap indicates..."
  ],
  "similarity_scores": [0.84, 0.71],
  "grounded": true
}
```

**Irrelevant question:**
```json
{
  "answer": "I don't have information about this in the provided document.",
  "sources": [],
  "similarity_scores": [],
  "grounded": false
}
```

---

## What I Learned

1. **Data leakage exists in RAG too** — if you fit your chunking strategy using test queries, you're cheating. The chunking strategy must be fixed before seeing any queries.

2. **The relevance threshold is the most important hyperparameter** — too low and the model halluccinates on unrelated questions, too high and it says "I don't know" even when it has relevant context. I landed on 0.5 after testing with 20 diverse questions.

3. **Singleton pattern for models is non-negotiable** — loading `sentence-transformers` takes ~3 seconds. Loading it on every request would make the API unusable. Loading once at startup makes every request ~200ms.

4. **ChromaDB distance scores are inverted** — lower distance = more similar. A distance of 0 = identical. This tripped me up when writing the relevance check.

5. **Chunk overlap prevents losing answers at boundaries** — without overlap, if a key sentence was split across two chunks, neither chunk would have enough context to answer the question. 50-token overlap fixes this.

---

## What I'd Improve

- **Semantic chunking** instead of fixed-size token chunking — split at paragraph/sentence boundaries for more coherent chunks
- **Re-ranking** — retrieve top-10, then re-rank to top-3 using a cross-encoder model for better precision
- **Streaming responses** — stream the LLM output token-by-token for faster perceived response time
- **Multi-document support** — ingest multiple documents and tag chunks with their source filename
- **Evaluation framework** — RAGAS library to automatically measure faithfulness and answer relevance

---

## Interview Hook

> *"I tested the system with 15 questions — 10 covered by the document, 5 not. Without the relevance threshold, the model answered all 15 but hallucinated on the 5 out-of-scope ones. With the threshold at 0.5, it correctly said 'I don't have information on this' for all 5 irrelevant questions and answered the 10 relevant ones accurately. That's the core engineering value of RAG."*
