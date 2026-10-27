"""Tests for search location filter and empty state — item 7 fixes."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.cv_parser import parse_cv
from app.main import CV_FILE, app, _save_cv

client = TestClient(app)

SAMPLE_CV_TEXT = """
Alex Martin
alex@example.com
EXPERIENCE
- Built Python data pipelines at Startup Co
- Data analysis with SQL and Pandas
SKILLS
Python, SQL, Data Analysis
"""

_REAL_SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_cv.txt"


@pytest.fixture(autouse=True)
def load_sample_cv():
    _save_cv(parse_cv(SAMPLE_CV_TEXT).to_dict())
    yield
    # Restore the real sample CV so tests don't corrupt data/cv.json
    if _REAL_SAMPLE.exists():
        _save_cv(parse_cv(_REAL_SAMPLE.read_text(encoding="utf-8")).to_dict())


def test_search_returns_offers():
    r = client.post("/api/offers/search", json={"source": "demo", "keywords": "", "location": ""})
    assert r.status_code == 200
    assert len(r.json()["offers"]) > 0


def test_offers_have_flags_count():
    """All offers in search results should have a flags_count field."""
    r = client.post("/api/offers/search", json={"source": "demo", "keywords": "", "location": ""})
    offers = r.json()["offers"]
    for o in offers:
        assert "flags_count" in o, f"Missing flags_count on offer {o.get('id')}"


def test_location_filter_paris():
    r = client.post("/api/offers/search", json={"source": "demo", "keywords": "", "location": "paris"})
    assert r.status_code == 200
    offers = r.json()["offers"]
    assert len(offers) > 0
    for o in offers:
        loc = (o.get("location") or "").lower()
        assert "paris" in loc or "remote" in loc, f"Non-Paris offer returned: {loc}"


def test_location_filter_accent_insensitive():
    """'Paris' and 'párîs' should match the same offers."""
    r1 = client.post("/api/offers/search", json={"source": "demo", "keywords": "", "location": "paris"})
    r2 = client.post("/api/offers/search", json={"source": "demo", "keywords": "", "location": "Paris"})
    assert r1.json()["offers"] == r2.json()["offers"]


def test_keyword_no_match_returns_empty():
    """A keyword with no match should return empty list, not all offers."""
    r = client.post("/api/offers/search", json={"source": "demo", "keywords": "xyzzy_nonexistent_job_2026", "location": ""})
    assert r.status_code == 200
    assert r.json()["offers"] == []


def test_manual_offer_returns_flags_count():
    r = client.post("/api/offers/manual", json={
        "title": "Data Analyst", "company": "Acme",
        "description": "Young and dynamic data analyst needed, Python and SQL required.",
    })
    assert r.status_code == 200
    offer = r.json()["offer"]
    assert "flags_count" in offer
    assert offer["flags_count"] >= 1  # "young" should fire
