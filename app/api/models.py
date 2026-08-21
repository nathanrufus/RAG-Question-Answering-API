"""
models.py — Pydantic schemas for every API request and response.

LEARNING NOTE — Why Pydantic models instead of plain dicts?
  FastAPI uses these models to:
    1. VALIDATE incoming requests — if 'question' is missing → 422 error automatically
    2. DOCUMENT the API — every field appears in /docs with its type and description
    3. SERIALISE responses — Python objects → JSON automatically
  
  Without Pydantic, you'd write manual validation:
    if "question" not in body: return {"error": "missing question"}
    if not isinstance(body["question"], str): return {"error": "..."}
  
  Pydantic does all of this in one line: question: str
  
  Field() lets you add constraints (min_length, gt=0) and descriptions
  that appear in the auto-generated API documentation at /docs.
"""

from pydantic import BaseModel, Field


# ── Ingest ────────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    file_path: str = Field(
        ...,  # ... means required (no default)
        description="Path to a .txt or .md file to ingest",
        examples=["sample_docs/ml_basics.txt"],
    )


class IngestResponse(BaseModel):
    message: str
    file: str
    chunks_stored: int = Field(description="Number of chunks added to the vector store")


# ── Query ─────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The question to answer using the ingested document",
        examples=["What is overfitting?"],
    )
    top_k: int = Field(
        default=3,
        ge=1,    # greater than or equal to 1
        le=10,   # less than or equal to 10
        description="Number of document chunks to retrieve (1-10)",
    )


class QueryResponse(BaseModel):
    answer: str = Field(description="The generated answer, grounded in the document")
    sources: list[str] = Field(description="The exact document chunks used to generate the answer")
    similarity_scores: list[float] = Field(
        description="Similarity score per source chunk (0.0-1.0, higher = more relevant)"
    )
    grounded: bool = Field(
        description="True if a relevant chunk was found. False if the question is outside the document's scope."
    )


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    chunks_stored: int = Field(description="Total chunks currently in the vector store")


# ── Error ─────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Consistent error shape returned for all 4xx and 5xx errors."""
    error: str = Field(description="Short error code (snake_case)")
    message: str = Field(description="Human-readable description of what went wrong")
    status_code: int
