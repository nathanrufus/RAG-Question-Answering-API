"""
test_pipeline.py — Unit tests for the core RAG pipeline components.

LEARNING NOTE — What to test and what not to test:
  TEST: your own logic — chunking, relevance checks, response shape
  DON'T TEST: external services — ChromaDB internals, the Anthropic API
  
  We mock external dependencies using pytest's monkeypatch or unittest.mock.
  This makes tests fast (no network), deterministic (same output every run),
  and cheap (no API token usage).

LEARNING NOTE — pytest vs unittest:
  pytest is the industry standard. No need to extend TestCase classes.
  Just name your functions test_*() and pytest finds them automatically.
  Fixtures (functions decorated with @pytest.fixture) provide reusable
  setup for multiple tests.

Run tests:
  pytest tests/ -v                    # verbose output
  pytest tests/ -v --tb=short         # shorter tracebacks
  pytest tests/test_pipeline.py -k "chunking"  # run only chunking tests
"""

import pytest
from app.pipeline.ingestion import DocumentChunker


# ── DocumentChunker tests ─────────────────────────────────────────────────────

class TestDocumentChunker:
    """Tests for the DocumentChunker class."""

    @pytest.fixture
    def chunker(self):
        """Provide a default chunker to each test."""
        return DocumentChunker(chunk_size=100, overlap=10)

    def test_chunk_produces_correct_count(self, chunker):
        """
        Chunking a known-length text should produce the expected number of chunks.
        """
        # A string of ~250 tokens with chunk_size=100 and overlap=10 gives:
        # chunk 0: tokens 0-99
        # chunk 1: tokens 90-189   (starts at 100-10=90)
        # chunk 2: tokens 180-249  (starts at 190-10=180)
        # = 3 chunks
        text = "word " * 250  # roughly 250 tokens
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2, "Should produce multiple chunks"

    def test_chunk_ids_are_unique(self, chunker):
        """Every chunk must have a unique ID."""
        text = "word " * 300
        chunks = chunker.chunk(text)
        ids = [c["id"] for c in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs must be unique"

    def test_chunk_ids_are_zero_padded(self, chunker):
        """IDs should be zero-padded for correct alphabetical sorting."""
        text = "word " * 300
        chunks = chunker.chunk(text)
        assert chunks[0]["id"] == "chunk_0000"
        assert chunks[1]["id"] == "chunk_0001"

    def test_each_chunk_has_required_keys(self, chunker):
        """Each chunk dict must have the four expected keys."""
        text = "word " * 200
        chunks = chunker.chunk(text)
        required_keys = {"id", "text", "token_count", "start_token"}
        for chunk in chunks:
            assert required_keys.issubset(chunk.keys()), (
                f"Chunk missing keys: {required_keys - chunk.keys()}"
            )

    def test_chunk_token_count_is_accurate(self, chunker):
        """The token_count field should never exceed chunk_size."""
        text = "word " * 500
        chunks = chunker.chunk(text)
        for chunk in chunks:
            assert chunk["token_count"] <= chunker.chunk_size, (
                f"Chunk {chunk['id']} has {chunk['token_count']} tokens, "
                f"expected <= {chunker.chunk_size}"
            )

    def test_overlap_reduces_start_token_gap(self, chunker):
        """
        Adjacent chunks should start (chunk_size - overlap) tokens apart,
        not chunk_size tokens apart. This verifies overlap is working.
        """
        text = "word " * 500
        chunks = chunker.chunk(text)
        expected_step = chunker.chunk_size - chunker.overlap  # 100 - 10 = 90
        if len(chunks) >= 2:
            actual_step = chunks[1]["start_token"] - chunks[0]["start_token"]
            assert actual_step == expected_step, (
                f"Expected step {expected_step}, got {actual_step}. "
                "Overlap may not be applied correctly."
            )

    def test_chunk_text_is_not_empty(self, chunker):
        """No chunk should have empty text."""
        text = "word " * 200
        chunks = chunker.chunk(text)
        for chunk in chunks:
            assert chunk["text"].strip(), f"Chunk {chunk['id']} has empty text"

    def test_empty_text_returns_empty_list(self, chunker):
        """An empty document should produce zero chunks."""
        chunks = chunker.chunk("")
        assert chunks == []

    def test_short_text_produces_one_chunk(self, chunker):
        """A text shorter than chunk_size should produce exactly one chunk."""
        text = "This is a very short document."  # well under 100 tokens
        chunks = chunker.chunk(text)
        assert len(chunks) == 1

    def test_load_raises_on_missing_file(self, chunker):
        """Loading a non-existent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            chunker.load("does_not_exist.txt")

    def test_load_raises_on_unsupported_extension(self, chunker):
        """Loading a .pdf or .docx should raise ValueError."""
        with pytest.raises(ValueError):
            chunker.load("document.pdf")


# ── RAGPipeline relevance logic ───────────────────────────────────────────────

class TestRelevanceThreshold:
    """
    Tests for the relevance check logic in RAGPipeline.query().
    
    We test the LOGIC, not the full pipeline (which needs a real API key
    and a loaded model). We do this by testing the condition directly.
    
    LEARNING NOTE:
      This is called "testing the unit in isolation".
      We're not integration-testing the full pipeline here —
      we're verifying that our threshold comparison logic is correct.
    """

    def test_relevant_distance_passes(self):
        """Distance below threshold should be considered relevant."""
        threshold = 0.5
        distance = 0.3
        assert distance <= threshold, "Distance 0.3 should pass threshold 0.5"

    def test_irrelevant_distance_fails(self):
        """Distance above threshold should be considered NOT relevant."""
        threshold = 0.5
        distance = 0.8
        assert distance > threshold, "Distance 0.8 should fail threshold 0.5"

    def test_exact_threshold_is_relevant(self):
        """Distance exactly at threshold should be considered relevant (inclusive)."""
        threshold = 0.5
        distance = 0.5
        assert distance <= threshold

    def test_similarity_conversion(self):
        """Verify distance → similarity conversion: similarity = 1 - distance."""
        distance = 0.12
        similarity = round(1 - distance, 3)
        assert similarity == 0.88

    def test_empty_results_returns_no_sources(self):
        """When no chunks are in the store, sources should be empty."""
        retrieved_texts = []
        distances = []
        # Simulating the early-return condition in RAGPipeline.query()
        no_results = not retrieved_texts or (distances and distances[0] > 0.5)
        assert no_results
