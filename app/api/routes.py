"""
routes.py — FastAPI route handlers for all endpoints.

LEARNING NOTE — APIRouter vs putting routes directly on app:
  We use APIRouter here and mount it with a prefix in main.py.
  This keeps routes modular — you can add a v2 router later
  without touching v1. It's the standard FastAPI pattern for
  any app with more than 2-3 endpoints.

LEARNING NOTE — Dependency injection with Depends():
  `pipeline: RAGPipeline = Depends(get_pipeline)` tells FastAPI:
    "Before calling this function, call get_pipeline() and inject
     its return value as the 'pipeline' parameter."
  
  Why not just import the pipeline directly?
    Testing: you can swap get_pipeline() for a mock in tests
    Flexibility: you could swap the pipeline implementation
    Explicitness: makes dependencies visible in the function signature

LEARNING NOTE — async def vs def:
  Use `async def` for route handlers. FastAPI runs them in an async
  event loop. If you call a slow function (LLM API, DB query) with
  `await`, FastAPI can handle other requests while waiting.
  If you don't have async calls inside, `def` also works but is
  slightly less efficient under concurrent load.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.models import (
    IngestRequest, IngestResponse,
    QueryRequest, QueryResponse,
    HealthResponse,
)
from app.pipeline.rag import RAGPipeline
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ── Dependency ────────────────────────────────────────────────────────────────

def get_pipeline(request: Request) -> RAGPipeline:
    """
    Retrieve the RAGPipeline singleton from app state.
    
    The pipeline is stored on app.state in main.py lifespan().
    Depends(get_pipeline) injects it into every route that needs it.
    """
    return request.app.state.pipeline


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check(pipeline: RAGPipeline = Depends(get_pipeline)):
    """
    Check that the API is running and return how many chunks are stored.
    
    This is always the first endpoint you implement and test.
    Production systems ping /health every 30 seconds to detect crashes.
    """
    return HealthResponse(
        status="ok",
        chunks_stored=pipeline.store.count(),
    )


@router.post("/ingest", response_model=IngestResponse, tags=["RAG"], status_code=201)
async def ingest_document(
    request: IngestRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
):
    """
    Ingest a document into the vector store.
    
    Flow: load file → chunk → embed → store in ChromaDB.
    Returns 201 Created with the number of chunks stored.
    
    LEARNING NOTE — status_code=201:
      201 Created is correct for endpoints that CREATE a new resource.
      200 OK is for retrieving existing resources.
      Most beginners use 200 for everything — using the right code
      shows you understand REST conventions.
    """
    try:
        result = pipeline.ingest(request.file_path)
        return IngestResponse(
            message="Ingested successfully",
            file=result["file"],
            chunks_stored=result["chunks_stored"],
        )
    except FileNotFoundError as e:
        # 404: the client asked for a file that doesn't exist
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        # 400: the client sent a bad file type
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/query", response_model=QueryResponse, tags=["RAG"])
async def query_document(
    request: QueryRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
):
    """
    Answer a question using the ingested document.
    
    Flow: embed question → retrieve chunks → relevance check →
          augment prompt → generate → return answer + sources.
    
    Returns grounded=False if the question isn't covered by the document.
    The LLM is never called for irrelevant questions (saves tokens + latency).
    """
    if pipeline.store.count() == 0:
        raise HTTPException(
            status_code=400,
            detail="No document ingested yet. POST to /v1/ingest first.",
        )

    try:
        result = pipeline.query(
            question=request.question,
            top_k=request.top_k,
        )
        return QueryResponse(**result)
    except Exception as e:
        logger.error(
            "Query failed",
            extra={"extra": {"error": str(e), "question": request.question}}
        )
        raise HTTPException(status_code=500, detail="Query failed. Check server logs.")


@router.delete("/collection", tags=["System"])
async def clear_collection(pipeline: RAGPipeline = Depends(get_pipeline)):
    """
    Clear the vector store and start fresh.
    
    Use this between experiments or when you want to ingest a new document.
    """
    pipeline.store.clear()
    return {"message": "Collection cleared. Ingest a new document to begin."}
