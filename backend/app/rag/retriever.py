"""Turn a plan into search queries and fetch the guideline passages that explain it."""
from typing import Dict, List, Tuple

from .chunking import Chunk
from .store import Embedder, VectorIndex

CROP_WORDS = {"Paddy": "rice paddy", "Groundnut": "groundnut", "Maize": "maize",
              "Cotton": "cotton", "Chilli": "chilli", "Redgram": "redgram pigeonpea"}


def plan_queries(soil: Dict[str, float], crop: str, ratings: Dict[str, str]) -> List[Tuple[str, str]]:
    """(topic, query) pairs: one per decision the rule engine made."""
    c = CROP_WORDS.get(crop, crop.lower())
    queries = [("dose", f"soil test based fertiliser recommendation nitrogen phosphorus potassium dose for {c}")]
    if ratings.get("p") == "High":
        queries.append(("phosphorus", "high soil phosphorus reduce DAP phosphate fertiliser overuse"))
    if soil["zn"] < 0.6:
        queries.append(("zinc", f"zinc deficiency zinc sulphate application in {c} soil"))
    if crop == "Groundnut":
        queries.append(("gypsum", "gypsum application at flowering groundnut pod filling calcium"))
    if ratings.get("oc") == "Low":
        queries.append(("organic", "low organic carbon farmyard manure organic matter soil health"))
    if soil["ph"] > 8.0 or soil["ph"] < 6.5:
        queries.append(("ph", "soil pH alkaline acidic nutrient availability amendment"))
    return queries


def retrieve(index: VectorIndex, embedder: Embedder, queries: List[Tuple[str, str]],
             per_query: int = 2, limit: int = 6, min_score: float = 0.6) -> List[Tuple[str, Chunk, float]]:
    """Best passages per query, de-duplicated, at most `limit` overall.

    The top passage of every topic is kept first, so one strong topic cannot crowd out the others.
    """
    if index is None or not queries:
        return []
    vectors = embedder.embed([q for _, q in queries])
    seen, firsts, rest = set(), [], []
    for (topic, _), vec in zip(queries, vectors):
        for rank, (chunk, score) in enumerate(index.search(vec, k=per_query, min_score=min_score)):
            key = (chunk.doc, chunk.page)  # one citation per page
            if key not in seen:
                seen.add(key)
                (firsts if rank == 0 else rest).append((topic, chunk, score))
    firsts.sort(key=lambda r: -r[2])
    rest.sort(key=lambda r: -r[2])
    return (firsts + rest)[:limit]
