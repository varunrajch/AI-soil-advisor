"""Build the vector index from every PDF in docs/.

Usage (from the project root):  python3 -m backend.app.rag.ingest
"""
import logging
import time

from ..config import settings
from ..logging_setup import log, setup_logging
from .chunking import chunk_pdf, read_sources
from .store import VectorIndex, get_embedder

logger = logging.getLogger("nela.rag.ingest")


def build_index(docs_dir=settings.docs_dir, index_dir=settings.index_dir, embedder=None) -> VectorIndex:
    meta = read_sources(docs_dir)
    chunks = []
    for pdf in sorted(docs_dir.glob("*.pdf")):
        info = meta.get(pdf.name, {})
        title = info.get("title", pdf.stem.replace("_", " "))
        doc_chunks = chunk_pdf(pdf, title, info.get("url"))
        log(logger, logging.INFO, "ingest.doc", doc=pdf.name, chunks=len(doc_chunks))
        chunks.extend(doc_chunks)
    start = time.perf_counter()
    index = VectorIndex.build(chunks, embedder or get_embedder(settings.embed_model))
    index.save(index_dir)
    log(logger, logging.INFO, "ingest.done", chunks=len(chunks), dir=str(index_dir),
        ms=round((time.perf_counter() - start) * 1000))
    return index


if __name__ == "__main__":
    setup_logging()
    build_index()
