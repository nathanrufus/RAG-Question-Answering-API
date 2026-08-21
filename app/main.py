"""
main.py — FastAPI application entry point.

LEARNING NOTE — lifespan() replaces the old @app.on_event("startup"):
  lifespan is the modern FastAPI pattern (v0.93+) for startup/shutdown logic.
  Code BEFORE `yield` runs at startup.
  Code AFTER `yield` runs at shutdown.
  
  We load the RAGPipeline here — once — and store it on app.state.
  Every request then gets it via Depends(get_pipeline) in routes.py.
  
  Why app.state?
    It's FastAPI's built-in place to store application-level objects
    (things that persist across requests). It's thread-safe and accessible
    from any route handler via request.app.state.

LEARNING NOTE — Global exception handler:
  Without this, any unhandled exception returns HTML (FastAPI's default).
  That's terrible for an API — clients expect JSON, not HTML stack traces.
  The global handler catches EVERYTHING and returns consistent JSON.
  
  Your specific HTTPException handlers still fire first for 4xx errors —
  the global handler is only the final fallback for unexpected crashes.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.routes import router
from app.pipeline.rag import RAGPipeline
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ── Lifespan: startup & shutdown ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Everything before `yield` runs at startup.
    Everything after `yield` runs at shutdown.
    """
    logger.info("Starting RAG API — loading pipeline...")
    
    # Load the pipeline ONCE. The Embedder downloads ~90MB on first run.
    # Subsequent startups use the cached model from ~/.cache/huggingface/
    app.state.pipeline = RAGPipeline()
    
    logger.info("RAG API ready — accepting requests")
    
    yield  # ← API is live here
    
    logger.info("RAG API shutting down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="RAG Question-Answering API",
    description="Ingest any document and answer questions grounded only in that document.",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount all /v1/* routes
# The prefix means: routes.py defines "/health" but it's reachable at "/v1/health"
# The tags group endpoints in the /docs UI
app.include_router(router, prefix="/v1")


# ── Global error handlers ─────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    422 Unprocessable Entity — Pydantic validation failed.
    
    Triggered when the request body doesn't match the Pydantic model.
    Example: sending {"question": 123} when question must be a string.
    
    FastAPI returns 422 automatically, but we reformat it to match
    our consistent error shape: {error, message, status_code}.
    """
    errors = exc.errors()
    # Build a readable summary of all validation failures
    details = "; ".join(
        f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}"
        for e in errors
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": details,
            "status_code": 422,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    500 Internal Server Error — something crashed unexpectedly.
    
    This is the catch-all. If nothing else handles an exception, it lands here.
    We log the full error (so we can debug) and return clean JSON (so clients
    don't receive HTML stack traces).
    
    LEARNING NOTE:
      In production you'd also send the error to an alerting system
      (Sentry, Datadog, PagerDuty) so your team is notified immediately.
    """
    logger.error(
        "Unhandled exception",
        extra={"extra": {
            "error": str(exc),
            "type": type(exc).__name__,
            "path": request.url.path,
        }}
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Check server logs.",
            "status_code": 500,
        },
    )
