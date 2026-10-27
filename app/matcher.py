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

import json
import os
import threading
from pathlib import Path

import numpy as np

from .skills import extract_skills

EMBED_MODEL = os.getenv("LANDED_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
W_SEMANTIC, W_SKILLS = 0.6, 0.4
DATA = Path(__file__).resolve().parent.parent / "data"

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


def similarities(query: str, docs: list[str], doc_embeddings: np.ndarray | None = None) -> np.ndarray:
    """Cosine similarity between `query` and each doc, in [0, 1].

    `doc_embeddings`, when given, skips re-encoding `docs` (see `cached_embeddings`
    for datasets large enough that re-encoding on every search is too slow).
    """
    if not docs:
        return np.array([])
    _load()
    if _backend == "sentence-transformers":
        if doc_embeddings is None:
            doc_embeddings = _model.encode(docs, normalize_embeddings=True, show_progress_bar=False)
        q_emb = _model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        sims = doc_embeddings @ q_emb
        # MiniLM cosine for related texts lives roughly in [0.1, 0.75]: rescale to [0, 1]
        return np.clip((sims - 0.10) / 0.60, 0, 1)
    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    m = vec.fit_transform([query] + docs)
    sims = (m[1:] @ m[0].T).toarray().ravel()
    return np.clip(sims / 0.35, 0, 1)


def offer_text(o: dict) -> str:
    return f"{o.get('title', '')}. {o.get('company', '')}. {o.get('description', '')}"


def cached_embeddings(offers: list[dict], cache_name: str) -> np.ndarray | None:
    """Return (building + persisting on first call) sentence-embeddings for a fixed
    list of offers, keyed by `cache_name` (e.g. "offers_fr"). Saved as
    data/<cache_name>_emb.npy + data/<cache_name>_emb_ids.json so a later run reloads
    instead of re-encoding. Returns None when running on the TF-IDF fallback backend,
    since TF-IDF vectors depend on the query and can't be precomputed per-doc; the
    caller then falls back to on-the-fly encoding via `similarities`.
    """
    _load()
    if _backend != "sentence-transformers":
        return None
    emb_path = DATA / f"{cache_name}_emb.npy"
    ids_path = DATA / f"{cache_name}_emb_ids.json"
    ids = [o["id"] for o in offers]
    if emb_path.exists() and ids_path.exists():
        try:
            if json.loads(ids_path.read_text()) == ids:
                return np.load(emb_path)
        except Exception:  # noqa: BLE001 - corrupt cache, rebuild below
            pass
    emb = _model.encode([offer_text(o) for o in offers], normalize_embeddings=True, show_progress_bar=False)
    np.save(emb_path, emb)
    ids_path.write_text(json.dumps(ids))
    return emb


def cached_offer_skills(offers: list[dict], cache_name: str) -> list[list[str]]:
    """Return (building + persisting on first call) `extract_skills(offer_text(o))`
    for each offer in a fixed list, keyed by `cache_name`. The regex-based extractor
    runs ~50 patterns per offer, which is the real bottleneck (not embeddings) when
    ranking thousands of offers on every search, so it's cached the same way.
    """
    skills_path = DATA / f"{cache_name}_skills.json"
    ids = [o["id"] for o in offers]
    if skills_path.exists():
        try:
            cached = json.loads(skills_path.read_text())
            if cached.get("ids") == ids:
                return cached["skills"]
        except Exception:  # noqa: BLE001 - corrupt cache, rebuild below
            pass
    skills = [extract_skills(offer_text(o)) for o in offers]
    skills_path.write_text(json.dumps({"ids": ids, "skills": skills}, ensure_ascii=False))
    return skills


def rank_offers(cv_text: str, cv_skills: list[str], offers: list[dict],
               doc_embeddings: np.ndarray | None = None,
               offer_skills: list[list[str]] | None = None) -> list[dict]:
    if not offers:
        return []
    sims = similarities(cv_text, [offer_text(o) for o in offers], doc_embeddings)
    cv_set = set(cv_skills)
    ranked = []
    for i, (o, sem) in enumerate(zip(offers, sims)):
        req = offer_skills[i] if offer_skills is not None else extract_skills(offer_text(o))
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
