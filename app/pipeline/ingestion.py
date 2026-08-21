"""
ingestion.py — Load a document and split it into overlapping token chunks.

LEARNING NOTE — Why chunk at all?
  LLMs have a context window limit (e.g. 200k tokens for Claude).
  Even if your document fits, sending ALL of it wastes tokens and money.
  We only send the RELEVANT parts — that's the entire point of RAG.

LEARNING NOTE — Why overlap?
  Imagine a key sentence that happens to land exactly on a chunk boundary:
    Chunk A ends with: "...overfitting occurs when"
    Chunk B starts with: "the model memorises noise..."
  
  Neither chunk alone answers "What is overfitting?".
  50-token overlap means both chunks include "overfitting occurs when
  the model memorises noise" — the answer is always complete.

LEARNING NOTE — Why tiktoken (token counting) instead of word/character splitting?
  LLMs think in tokens, not words or characters. "unbelievable" = 1 token.
  "Nathan" = 2 tokens. Splitting by characters or words produces
  inconsistent chunk sizes when measured in tokens.
  tiktoken gives exact token counts — same as the LLM sees.
"""

from pathlib import Path
import tiktoken
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentChunker:
    def __init__(
        self,
        chunk_size: int = settings.chunk_size,
        overlap: int = settings.chunk_overlap,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        # cl100k_base is the tokenizer used by GPT-4 and Claude-compatible models
        self.enc = tiktoken.get_encoding("cl100k_base")

    def load(self, file_path: str) -> str:
        """Read a text file from disk."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        if path.suffix not in {".txt", ".md"}:
            raise ValueError(f"Unsupported file type: {path.suffix}. Use .txt or .md")
        return path.read_text(encoding="utf-8")

    def chunk(self, text: str) -> list[dict]:
        """
        Split text into overlapping token chunks.
        
        Returns a list of dicts, each with:
          - id:          unique chunk identifier
          - text:        the decoded chunk text
          - token_count: number of tokens in this chunk
          - start_token: position in the original token sequence
        
        Example with chunk_size=5, overlap=2, tokens=[1,2,3,4,5,6,7]:
          Chunk 0: tokens[0:5] = [1,2,3,4,5]
          Chunk 1: tokens[3:8] = [3,4,5,6,7]  ← starts 2 tokens back (overlap)
        """
        tokens = self.enc.encode(text)
        total_tokens = len(tokens)
        chunks = []
        start = 0
        chunk_idx = 0

        while start < total_tokens:
            end = min(start + self.chunk_size, total_tokens)
            chunk_tokens = tokens[start:end]
            chunk_text = self.enc.decode(chunk_tokens)

            chunks.append({
                "id": f"chunk_{chunk_idx:04d}",   # zero-padded: chunk_0001, chunk_0002
                "text": chunk_text,
                "token_count": len(chunk_tokens),
                "start_token": start,
            })

            # Slide forward by (chunk_size - overlap)
            # If chunk_size=512 and overlap=50, each chunk starts 462 tokens later
            start += self.chunk_size - self.overlap
            chunk_idx += 1

        logger.info(
            "Chunking complete",
            extra={"extra": {
                "total_tokens": total_tokens,
                "chunk_count": len(chunks),
                "chunk_size": self.chunk_size,
                "overlap": self.overlap,
            }}
        )
        return chunks

    def load_and_chunk(self, file_path: str) -> list[dict]:
        """Convenience method: load a file and chunk it in one call."""
        text = self.load(file_path)
        return self.chunk(text)
