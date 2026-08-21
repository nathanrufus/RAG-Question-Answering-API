"""
embedder.py — Convert text into high-dimensional vectors using sentence-transformers.

LEARNING NOTE — What is an embedding?
  An embedding converts text into a list of numbers (a vector).
  
  "I love Python"  → [0.12, -0.34, 0.87, ...]   (384 numbers)
  "Python is great" → [0.11, -0.31, 0.85, ...]  (384 numbers — very similar!)
  "I hate rain"    → [-0.45, 0.22, -0.12, ...]  (384 numbers — very different)
  
  Similar MEANING → similar vectors → small cosine distance.
  This is why semantic search works: "What is overfitting?" finds
  the chunk that says "Overfitting occurs when..." even though
  no exact words overlap.

LEARNING NOTE — Why all-MiniLM-L6-v2?
  - 384 dimensions (fast, small)
  - Good quality for general-purpose semantic search
  - Runs locally (free, no API call, no rate limit)
  - The "L6" means 6 transformer layers — small but effective
  - Larger alternative: all-mpnet-base-v2 (768 dims, slower, more accurate)

LEARNING NOTE — Cosine distance vs dot product:
  Cosine distance ignores vector length and only measures direction/angle.
  This makes it length-independent: a long paragraph and a short sentence
  on the same topic are equally similar to a query.
  Dot product is sensitive to vector magnitude — longer text = larger vectors
  = higher dot product even if the topic is different.
"""

from sentence_transformers import SentenceTransformer
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Embedder:
    def __init__(self, model_name: str = settings.embed_model):
        logger.info("Loading embedding model", extra={"extra": {"model": model_name}})
        # This downloads the model on first run (~90MB), then caches it locally
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.dimensions = self.model.get_sentence_embedding_dimension()
        logger.info(
            "Embedding model loaded",
            extra={"extra": {"model": model_name, "dimensions": self.dimensions}}
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Convert a list of strings into a list of embedding vectors.
        
        Args:
            texts: List of strings to embed. Can be 1 or thousands.
        
        Returns:
            List of embedding vectors. Each vector is a list of floats.
            Shape: (len(texts), self.dimensions) — e.g. (24, 384)
        """
        if not texts:
            return []

        # batch encode — much faster than encoding one at a time
        # convert_to_numpy=False keeps them as Python lists for JSON serialisation
        vectors = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        
        # .tolist() converts numpy arrays to plain Python lists (JSON-serialisable)
        result = vectors.tolist()
        
        logger.info(
            "Embedded texts",
            extra={"extra": {"count": len(texts), "dimensions": self.dimensions}}
        )
        return result

    def embed_one(self, text: str) -> list[float]:
        """Convenience method: embed a single string."""
        return self.embed([text])[0]
