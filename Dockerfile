# ── Base image ────────────────────────────────────────────────────────────────
# python:3.11-slim = Python 3.11 on Debian, without dev tools (~130MB vs ~900MB for full image)
# Always pin to a specific version — never use :latest in production
FROM python:3.11-slim

# ── Working directory ─────────────────────────────────────────────────────────
# All subsequent commands run relative to /app inside the container
WORKDIR /app

# ── Install dependencies FIRST ────────────────────────────────────────────────
# LEARNING NOTE — Layer caching:
#   Docker builds images layer by layer. Each instruction = one layer.
#   If a layer hasn't changed since the last build, Docker reuses it (cached).
#
#   By copying requirements.txt FIRST and installing, this layer only
#   invalidates when requirements.txt changes — not when your code changes.
#   This means "code change only" builds skip re-installing packages (~3 min saved).
#
#   If you copied ALL files first, then ran pip install, any code change
#   would force a full package reinstall. Slow and wasteful.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Download the embedding model at build time ────────────────────────────────
# LEARNING NOTE:
#   sentence-transformers downloads the model on first use (~90MB).
#   If we let it happen at startup, the container takes ~30s to become ready.
#   Doing it at build time bakes the model INTO the image layer.
#   Container starts in ~3s. The image is larger but startup is instant.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── Copy application code ─────────────────────────────────────────────────────
# This layer invalidates on any code change — but packages are already cached above
COPY . .

# ── Create directory for ChromaDB persistence ─────────────────────────────────
RUN mkdir -p /app/chroma_db

# ── Expose the port ───────────────────────────────────────────────────────────
# This is documentation — it doesn't actually open the port.
# The port is opened by `docker run -p 8000:8000` at runtime.
EXPOSE 8000

# ── Startup command ───────────────────────────────────────────────────────────
# host=0.0.0.0 makes the server accessible from OUTSIDE the container.
# Default is 127.0.0.1 (localhost inside the container — unreachable from outside!).
# workers=1 for this demo — in production you'd calculate based on CPU cores.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
