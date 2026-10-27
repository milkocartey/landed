"""Landed - FastAPI server. Run with:  python -m app.main  (then open http://localhost:8000)"""
from __future__ import annotations

import asyncio
import json
import os
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


_load_env()

from fastapi import FastAPI, File, HTTPException, UploadFile  # noqa: E402
from fastapi.concurrency import run_in_threadpool  # noqa: E402
from fastapi.responses import FileResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from . import bias as bias_mod  # noqa: E402
from . import crm, export, generator, matcher, sources  # noqa: E402
from .cv_parser import parse_cv, read_file  # noqa: E402

app = FastAPI(title="Landed", version="1.0")
CV_FILE = ROOT / "data" / "cv.json"
_cv: dict | None = json.loads(CV_FILE.read_text()) if CV_FILE.exists() else None


def _save_cv(cv: dict) -> dict:
    global _cv
    _cv = cv
    CV_FILE.parent.mkdir(exist_ok=True)
    CV_FILE.write_text(json.dumps(cv, ensure_ascii=False, indent=1))
    return cv


def _need_cv() -> dict:
    if not _cv:
        raise HTTPException(400, "Upload a CV first.")
    return _cv


# ------------------------------------------------------------------ status & CV
@app.get("/api/status")
def status():
    return {
        "embeddings": matcher.backend(),
        "llm": generator.active_backend(),
        "llm_model": generator.OLLAMA_MODEL if generator.active_backend() == "ollama" else generator.HF_MODEL,
        "adzuna": sources.adzuna_available(),
        "cv": bool(_cv),
    }


@app.get("/api/cv")
def get_cv():
    return _cv or {}


@app.post("/api/cv")
async def upload_cv(file: UploadFile = File(...)):
    data = await file.read()
    try:
        text = read_file(file.filename or "cv.txt", data)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"Could not read this file: {e}")
    if len(text.strip()) < 80:
        raise HTTPException(400, "Almost no text found. Is it a scanned image? Export your CV as a text PDF.")
    return _save_cv(parse_cv(text).to_dict())


@app.post("/api/cv/sample")
def sample_cv():
    text = (ROOT / "data" / "sample_cv.txt").read_text(encoding="utf-8")
    return _save_cv(parse_cv(text).to_dict())


class CvTextReq(BaseModel):
    text: str

@app.post("/api/cv/text")
def upload_cv_text(req: CvTextReq):
    text = req.text.strip()
    if len(text) < 80:
        raise HTTPException(400, "Text is too short. Paste at least a few paragraphs from your CV.")
    return _save_cv(parse_cv(text).to_dict())


# ------------------------------------------------------------------ offers
class SearchReq(BaseModel):
    source: str = "demo"  # demo | adzuna
    keywords: str = ""
    location: str = ""


class ManualReq(BaseModel):
    title: str
    company: str = ""
    description: str
    url: str = ""
    location: str = ""
    source: str = "Manual"


def _norm(s: str) -> str:
    """Lowercase + strip accents for accent-insensitive comparison."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )


def _loc_match(offer: dict, loc_norm: str) -> bool:
    o_loc = _norm(offer.get("location", "") or "")
    return loc_norm in o_loc or "remote" in o_loc


@app.post("/api/offers/search")
def search(req: SearchReq):
    cv = _need_cv()
    if req.source == "adzuna":
        try:
            offers = sources.search_adzuna(req.keywords or " ".join(cv["skills"][:2]), req.location)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(502, f"Adzuna search failed: {e}")
    else:
        offers = sources.demo_offers()
        if req.location:
            loc_norm = _norm(req.location)
            loc_filtered = [o for o in offers if _loc_match(o, loc_norm)]
            if loc_filtered:
                offers = loc_filtered
        if req.keywords:
            kws = [k.lower() for k in req.keywords.split()]
            filtered = [o for o in offers if any(k in matcher.offer_text(o).lower() for k in kws)]
            offers = filtered  # return empty list if no keyword match (honest empty state)

    ranked = matcher.rank_offers(cv["raw_text"], cv["skills"], offers)

    # Annotate each offer with bias flag count for the UI badge
    for o in ranked:
        r = bias_mod.analyze_offer(o.get("description", ""))
        legal_count = len(r["legal"])
        excl_count = len(r["exclusionary"])
        o["flags_count"] = legal_count + excl_count
        o["flags_legal"] = legal_count

    return {"offers": ranked}


@app.post("/api/offers/manual")
def manual(req: ManualReq):
    cv = _need_cv()
    o = sources.manual_offer(req.title, req.company, req.description, req.url, req.location, req.source)
    ranked = matcher.rank_offers(cv["raw_text"], cv["skills"], [o])
    offer = ranked[0]
    r = bias_mod.analyze_offer(offer.get("description", ""))
    offer["flags_count"] = len(r["legal"]) + len(r["exclusionary"])
    offer["flags_legal"] = len(r["legal"])
    return {"offer": offer}


# ------------------------------------------------------------------ generation
class GenReq(BaseModel):
    offer: dict


@app.post("/api/generate")
async def generate(req: GenReq):
    cv = _need_cv()
    o = req.offer
    matched, missing = o.get("matched_skills", []), o.get("missing_skills", [])

    def _gen():
        return {
            "cv": generator.tailor_cv(cv, o, matched),
            "letter": generator.cover_letter(cv, o, matched, missing),
            "engine": generator.active_backend(),
        }

    try:
        return await asyncio.wait_for(run_in_threadpool(_gen), timeout=90.0)
    except asyncio.TimeoutError:
        return {
            "cv": generator._template_cv(cv, o, matched),
            "letter": {
                "text": generator._template_letter(cv, o, matched, missing),
                "flags": [],
                "engine": "template (90s timeout — paste your own text to edit)",
            },
            "engine": "template",
        }


class CvExport(BaseModel):
    cv: dict
    filename: str = "tailored_cv"


class LetterExport(BaseModel):
    text: str
    filename: str = "cover_letter"


DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@app.post("/api/export/cv")
def export_cv(req: CvExport):
    return Response(export.cv_docx(req.cv), media_type=DOCX,
                    headers={"Content-Disposition": f'attachment; filename="{req.filename}.docx"'})


@app.post("/api/export/letter")
def export_letter(req: LetterExport):
    return Response(export.letter_docx(req.text), media_type=DOCX,
                    headers={"Content-Disposition": f'attachment; filename="{req.filename}.docx"'})


# ------------------------------------------------------------------ bias
class BiasReq(BaseModel):
    description: str


class BiasTestReq(BaseModel):
    offer: dict


@app.post("/api/bias/offer")
def bias_offer(req: BiasReq):
    return bias_mod.analyze_offer(req.description)


@app.post("/api/bias/test")
def bias_test(req: BiasTestReq):
    cv = _need_cv()
    return bias_mod.counterfactual_test(cv, req.offer, matcher)


# ------------------------------------------------------------------ CRM
@app.get("/api/applications")
def apps():
    return crm.list_all()


@app.post("/api/applications")
def add_app(data: dict):
    return crm.create(data)


@app.patch("/api/applications/{app_id}")
def edit_app(app_id: int, data: dict):
    if not crm.get(app_id):
        raise HTTPException(404, "Not found")
    try:
        return crm.update(app_id, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/applications/{app_id}")
def del_app(app_id: int):
    crm.delete(app_id)
    return {"ok": True}


@app.get("/api/stats")
def stats():
    return crm.stats()


# ------------------------------------------------------------------ front-end
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    print(f"\n  Landed is running ->  http://localhost:{port}\n")
    uvicorn.run(app, host="127.0.0.1", port=port)
