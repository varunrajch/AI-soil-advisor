# One container: React build served by FastAPI.
# docker build -t nela-mitra . && docker run -p 8000:8000 -e GROQ_API_KEY=gsk_... nela-mitra

# ---- 1. build the React app ----
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 2. API + RAG index ----
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FASTEMBED_CACHE_PATH=/app/.cache/fastembed
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY engine.py extract.py ./
COPY backend/ backend/
COPY docs/ docs/
# Build the vector index at image build time (also downloads the embedding model once).
RUN python -m backend.app.rag.ingest

COPY --from=web /web/dist frontend/dist

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
