"""Hybrid CV <-> offer matching.

score = 0.6 * semantic similarity + 0.4 * skill coverage

* semantic similarity: cosine similarity between sentence embeddings of the CV and
  of the offer (sentence-transformers/all-MiniLM-L6-v2). If the model cannot be
  loaded (offline machine, no torch) we fall back to TF-IDF cosine similarity so the
  app always runs.
* skill coverage: share of the skills required by the offer that appear in the CV.

The same embedding model is reused to rank CV bullet points by relevance to an
offer when tailoring the CV (see generator.py).
"""
from __future__ import annotations

import os
import threading

import numpy as np

from .skills import extract_skills

EMBED_MODEL = os.getenv("LANDED_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
W_SEMANTIC, W_SKILLS = 0.6, 0.4

_model = None
_model_lock = threading.Lock()
_backend = "unloaded"


def _load():
    global _model, _backend
    with _model_lock:
        if _backend != "unloaded":
            return
        if os.getenv("LANDED_EMBEDDINGS", "auto") != "tfidf":
            try:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer(EMBED_MODEL)
                _backend = "sentence-transformers"
                return
            except Exception as e:  # noqa: BLE001
                print(f"[matcher] embeddings unavailable ({e.__class__.__name__}): using TF-IDF fallback")
        _backend = "tfidf"


def backend() -> str:
    _load()
    return _backend


def similarities(query: str, docs: list[str]) -> np.ndarray:
    """Cosine similarity between `query` and each doc, in [0, 1]."""
    if not docs:
        return np.array([])
    _load()
    if _backend == "sentence-transformers":
        emb = _model.encode([query] + docs, normalize_embeddings=True, show_progress_bar=False)
        sims = emb[1:] @ emb[0]
        # MiniLM cosine for related texts lives roughly in [0.1, 0.75]: rescale to [0, 1]
        return np.clip((sims - 0.10) / 0.60, 0, 1)
    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    m = vec.fit_transform([query] + docs)
    sims = (m[1:] @ m[0].T).toarray().ravel()
    return np.clip(sims / 0.35, 0, 1)


def offer_text(o: dict) -> str:
    return f"{o.get('title', '')}. {o.get('company', '')}. {o.get('description', '')}"


def rank_offers(cv_text: str, cv_skills: list[str], offers: list[dict]) -> list[dict]:
    if not offers:
        return []
    sims = similarities(cv_text, [offer_text(o) for o in offers])
    cv_set = set(cv_skills)
    ranked = []
    for o, sem in zip(offers, sims):
        req = extract_skills(offer_text(o))
        matched = [s for s in req if s in cv_set]
        missing = [s for s in req if s not in cv_set]
        coverage = len(matched) / len(req) if req else 0.5
        score = W_SEMANTIC * float(sem) + W_SKILLS * coverage
        ranked.append({
            **o,
            "score": round(100 * score),
            "semantic": round(100 * float(sem)),
            "coverage": round(100 * coverage),
            "matched_skills": matched,
            "missing_skills": missing,
        })
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked
