"""Chunking, the vector index and retrieval."""
import numpy as np

from backend.app.config import ROOT
from backend.app.rag.chunking import chunk_pages, clean, read_sources, split_text
from backend.app.rag.retriever import plan_queries, retrieve
from backend.app.rag.store import VectorIndex


def test_clean_joins_hyphenated_words():
    assert clean("ferti-\nliser   dose\n\n here") == "fertiliser dose here"


def test_split_text_windows_overlap():
    text = " ".join(f"word{i}" for i in range(400))
    chunks = split_text(text, size=300, overlap=60, min_len=50)
    assert len(chunks) > 3
    assert all(len(c) <= 320 for c in chunks)
    # the end of one chunk reappears at the start of the next
    assert chunks[0].split()[-1] in chunks[1].split()[:15]


def test_split_text_drops_tiny_pieces():
    assert split_text("too short", min_len=50) == []


def test_chunks_keep_page_numbers():
    pages = ["a " * 10, "zinc sulphate for rice " * 20]
    chunks = chunk_pages("x.pdf", pages, "X", None)
    assert chunks and all(c.page == 2 for c in chunks)


def test_read_sources_parses_docs_table():
    meta = read_sources(ROOT / "docs")
    assert "icar_indian_farming_rice_zinc.pdf" in meta
    assert meta["icar_indian_farming_rice_zinc.pdf"]["url"].startswith("https://")


def test_index_save_load_round_trip(tmp_path, small_index, embedder):
    small_index.save(tmp_path)
    loaded = VectorIndex.load(tmp_path)
    assert [c.doc for c in loaded.chunks] == [c.doc for c in small_index.chunks]
    q = embedder.embed(["gypsum groundnut flowering"])[0]
    assert loaded.search(q, k=1)[0][0].doc == "gypsum.pdf"


def test_missing_index_loads_as_none(tmp_path):
    assert VectorIndex.load(tmp_path) is None


def test_search_respects_min_score(small_index):
    assert small_index.search(np.ones(128, dtype=np.float32) * -1, k=3, min_score=0.5) == []


def test_plan_queries_follow_the_rules():
    soil = {"ph": 6.2, "zn": 0.5, "oc": 0.35}
    topics = [t for t, _ in plan_queries(soil, "Groundnut", {"p": "Low", "oc": "Low"})]
    assert topics == ["dose", "zinc", "gypsum", "organic", "ph"]
    topics = [t for t, _ in plan_queries({"ph": 7.0, "zn": 1.0, "oc": 0.8}, "Paddy", {"p": "High", "oc": "High"})]
    assert topics == ["dose", "phosphorus"]


def test_retrieve_keeps_one_passage_per_topic(small_index, embedder):
    queries = [("zinc", "zinc deficiency rice zinc sulphate"), ("gypsum", "gypsum groundnut flowering pod")]
    hits = retrieve(small_index, embedder, queries, per_query=2, limit=2, min_score=0.1)
    assert {topic for topic, _, _ in hits} == {"zinc", "gypsum"}
    assert len({(c.doc, c.page) for _, c, _ in hits}) == len(hits)
