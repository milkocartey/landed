"""Where offers come from.

1. Adzuna public API (free developer key, https://developer.adzuna.com) - live offers.
2. Arbeitnow public API (no key required, https://www.arbeitnow.com/api/job-board-api) - live offers.
3. France Travail API (free key: https://francetravail.io) - French job market, internships.
4. MyCareersFuture.sg (no key required, https://api.mycareersfuture.gov.sg) - Singapore jobs.
5. Manual import - paste any offer (JobTeaser, LinkedIn, Welcome to the Jungle...).
   No scraping: the user brings the text, which respects every site's terms of use.
6. Demo dataset - data/demo_offers.json, synthetic offers so the app works offline.
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


def search_arbeitnow(keywords: str, location: str = "", n: int = 30) -> list[dict]:
    """Public job board API — no key required. https://www.arbeitnow.com/api/job-board-api"""
    params: dict = {"search": keywords.strip() or "internship stage", "page": 1}
    r = requests.get("https://www.arbeitnow.com/api/job-board-api", params=params, timeout=20)
    r.raise_for_status()
    out = []
    loc_lower = location.lower()
    for j in r.json().get("data", [])[:n * 2]:
        job_location = j.get("location", "")
        if loc_lower and loc_lower not in job_location.lower():
            continue
        out.append({
            "id": "anw-" + str(j.get("slug") or _id(j.get("title", ""), j.get("company_name", ""))),
            "title": j.get("title", ""),
            "company": j.get("company_name", "Unknown company"),
            "location": job_location,
            "description": _clean(j.get("description", "")),
            "url": j.get("url", ""),
            "posted": "",
            "source": "Arbeitnow",
        })
        if len(out) >= n:
            break
    return out


def france_travail_available() -> bool:
    return bool(os.getenv("FRANCE_TRAVAIL_ID") and os.getenv("FRANCE_TRAVAIL_SECRET"))


def _france_travail_token() -> str:
    r = requests.post(
        "https://entreprise.francetravail.fr/connexion/oauth2/access_token",
        params={"realm": "/partenaire"},
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["FRANCE_TRAVAIL_ID"],
            "client_secret": os.environ["FRANCE_TRAVAIL_SECRET"],
            "scope": "api_offresdemploiv2 o2dsoffre",
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def search_france_travail(keywords: str, location: str = "", n: int = 30) -> list[dict]:
    if not france_travail_available():
        raise RuntimeError("France Travail keys missing: set FRANCE_TRAVAIL_ID and FRANCE_TRAVAIL_SECRET in .env")
    token = _france_travail_token()
    params: dict = {
        "motsCles": keywords.strip() or "stage",
        "natureContrat": "E1",  # E1 = convention de stage
        "range": f"0-{min(n, 149) - 1}",
    }
    if location:
        params["commune"] = location
    r = requests.get(
        "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        params=params,
        timeout=20,
    )
    r.raise_for_status()
    out = []
    for j in r.json().get("resultats", []):
        lieu = (j.get("lieuTravail") or {})
        out.append({
            "id": "ft-" + str(j.get("id") or _id(j.get("intitule", ""), j.get("entreprise", {}).get("nom", ""))),
            "title": j.get("intitule", ""),
            "company": (j.get("entreprise") or {}).get("nom", "Unknown company"),
            "location": lieu.get("libelle", ""),
            "description": _clean(j.get("description", "")),
            "url": j.get("origineOffre", {}).get("urlOrigine", ""),
            "posted": (j.get("dateCreation") or "")[:10],
            "source": "France Travail",
        })
    return out


def search_mycareersfuture(keywords: str, location: str = "", n: int = 30) -> list[dict]:
    """Singapore public jobs API — no key required. https://api.mycareersfuture.gov.sg"""
    params: dict = {
        "search": keywords.strip() or "internship",
        "limit": min(n, 100),
        "page": 0,
    }
    r = requests.get(
        "https://api.mycareersfuture.gov.sg/v2/jobs",
        headers={"Accept": "application/json"},
        params=params,
        timeout=20,
    )
    r.raise_for_status()
    out = []
    for j in r.json().get("results", []):
        metadata = j.get("metadata", {})
        position = j.get("position", {})
        company = (j.get("postedCompany") or j.get("originalityCompany") or {})
        out.append({
            "id": "mcf-" + str(metadata.get("jobPostId") or _id(position.get("title", ""), company.get("name", ""))),
            "title": position.get("title", ""),
            "company": company.get("name", "Unknown company"),
            "location": "Singapore",
            "description": _clean(j.get("description", "") or position.get("summary", "")),
            "url": f"https://www.mycareersfuture.gov.sg/job/{metadata.get('jobPostId', '')}",
            "posted": (metadata.get("originalPostingDate") or "")[:10],
            "source": "MyCareersFuture",
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
