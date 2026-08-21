"""
config.py — Centralised settings for the entire application.

LEARNING NOTE:
  pydantic-settings reads values from your .env file automatically.
  Every setting has a type annotation — if the value can't be cast
  to that type, pydantic raises an error at startup (fail fast).
  
  The alternative is os.getenv() scattered everywhere — messy and
  error-prone. Centralising config here means one place to look,
  and settings are validated before a single request is served.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- LLM ---
    gemini_api_key: str  # Required — no default. App won't start without it.
    # Model options:
    #   gemini-1.5-flash   → fast, cheap, good for retrieval tasks (recommended)
    #   gemini-1.5-pro     → slower, more capable, better for complex reasoning
    #   gemini-2.0-flash   → newest, fast, multimodal
    gemini_model: str = "gemini-1.5-flash"

    # --- Vector Store ---
    chroma_persist_dir: str = "./chroma_db"  # where ChromaDB saves vectors to disk

    # --- Embedding model ---
    # all-MiniLM-L6-v2: 384 dimensions, fast, free, runs locally.
    # Good balance of speed vs quality for semantic search.
    embed_model: str = "all-MiniLM-L6-v2"

    # --- Chunking ---
    # 512 tokens ≈ ~380 words ≈ 2-3 paragraphs.
    # 50 token overlap prevents an answer being split across two chunks.
    chunk_size: int = 512
    chunk_overlap: int = 50

    # --- Retrieval ---
    # top_k: how many chunks to pass to the LLM as context.
    # relevance_threshold: ChromaDB returns cosine *distance* (not similarity).
    #   distance 0 = identical, distance 1 = completely different.
    #   Above this threshold = "not relevant enough to use".
    top_k: int = 3
    relevance_threshold: float = 0.5

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


# Instantiate once at import time — used everywhere as `from app.config import settings`
settings = Settings()
