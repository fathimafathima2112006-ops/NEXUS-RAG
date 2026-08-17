import re
import numpy as np

from src.rag.indexer import load, model
from src.utils.config import TOP_K_RETRIEVE, TOP_K_FINAL

try:
    from sentence_transformers import CrossEncoder
except Exception:
    CrossEncoder = None

_reranker = None

def keyword_score(question, text):
    q = set(re.findall(r"\w+", question.lower()))
    t = set(re.findall(r"\w+", text.lower()))
    if not q:
        return 0.0
    return min(1.0, len(q & t) / len(q))

def reranker():
    global _reranker
    if _reranker is None and CrossEncoder:
        try:
            from src.utils.config import RERANKER_MODEL
            _reranker = CrossEncoder(RERANKER_MODEL)
        except Exception:
            _reranker = False
    return _reranker

def retrieve(question):
    index, metadata = load()
    if index is None or not metadata:
        return []

    q = model().encode(
        [question],
        normalize_embeddings=True,
        show_progress_bar=False
    ).astype("float32")

    k = min(max(TOP_K_RETRIEVE * 3, 20), len(metadata))
    scores, ids = index.search(q, k)

    candidates = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < 0:
            continue
        item = dict(metadata[int(idx)])
        item["semantic_score"] = float(score)
        item["keyword_score"] = keyword_score(question, item["text"])
        item["hybrid_score"] = (
            0.75 * item["semantic_score"]
            + 0.25 * item["keyword_score"]
        )
        candidates.append(item)

    candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)

    ranker = reranker()
    if ranker:
        pairs = [[question, x["text"]] for x in candidates[:TOP_K_RETRIEVE]]
        try:
            scores = ranker.predict(pairs)
            for item, score in zip(candidates, scores):
                item["rerank_score"] = float(score)
            candidates.sort(
                key=lambda x: x.get("rerank_score", -999),
                reverse=True
            )
        except Exception:
            pass

    return candidates[:TOP_K_FINAL]
