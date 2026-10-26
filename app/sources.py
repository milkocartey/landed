"""Where offers come from.

1. Adzuna public API (free developer key, https://developer.adzuna.com) - live offers.
2. Manual import - paste any offer (JobTeaser, LinkedIn, Welcome to the Jungle...).
   No scraping: the user brings the text, which respects every site's terms of use.
3. Demo dataset - data/demo_offers.json, synthetic offers so the app works offline.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parent.parent / "data"


def _id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]


def _clean(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def adzuna_available() -> bool:
    return bool(os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_APP_KEY"))


def search_adzuna(keywords: str, location: str = "", country: str = "fr",
                  internship_only: bool = True, n: int = 30) -> list[dict]:
    if not adzuna_available():
        raise RuntimeError("Adzuna keys missing: set ADZUNA_APP_ID and ADZUNA_APP_KEY in .env")
    what = keywords.strip()
    params = {
        "app_id": os.environ["ADZUNA_APP_ID"],
        "app_key": os.environ["ADZUNA_APP_KEY"],
        "results_per_page": min(n, 50),
        "what": what,
        "content-type": "application/json",
    }
    if internship_only:
        # Adzuna has no internship filter: require one of these words instead
        params["what_or"] = "stage stagiaire internship intern alternance"
    if location:
        params["where"] = location
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    out = []
    for j in r.json().get("results", []):
        title = _clean(j.get("title", ""))
        company = (j.get("company") or {}).get("display_name", "Unknown company")
        out.append({
            "id": "adz-" + str(j.get("id") or _id(title, company)),
            "title": title,
            "company": company,
            "location": (j.get("location") or {}).get("display_name", ""),
            "description": _clean(j.get("description", "")),
            "url": j.get("redirect_url", ""),
            "posted": (j.get("created") or "")[:10],
            "source": "Adzuna",
        })
    return out


def demo_offers() -> list[dict]:
    with open(DATA / "demo_offers.json", encoding="utf-8") as f:
        return json.load(f)


def manual_offer(title: str, company: str, description: str, url: str = "",
                 location: str = "", source: str = "Manual") -> dict:
    return {
        "id": "man-" + _id(title, company, description[:200]),
        "title": title.strip() or "Untitled offer",
        "company": company.strip() or "Unknown company",
        "location": location.strip(),
        "description": description.strip(),
        "url": url.strip(),
        "posted": "",
        "source": source or "Manual",
    }
