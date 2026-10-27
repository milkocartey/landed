"""Where offers come from.

1. Adzuna public API (free developer key, https://developer.adzuna.com) - live offers.
2. Indeed FR RSS feed (public, no auth) - live offers from indeed.fr.
3. Manual import - paste any offer (JobTeaser, LinkedIn, Welcome to the Jungle...).
   No scraping: the user brings the text, which respects every site's terms of use.
4. Demo dataset - data/demo_offers.json, synthetic offers so the app works offline.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
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


def france_travail_available() -> bool:
    return bool(os.getenv("FT_CLIENT_ID") and os.getenv("FT_CLIENT_SECRET"))


def _ft_token() -> str:
    r = requests.post(
        "https://entreprise.francetravail.fr/connexion/oauth2/access_token",
        params={"realm": "/partenaire"},
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["FT_CLIENT_ID"],
            "client_secret": os.environ["FT_CLIENT_SECRET"],
            "scope": "api_offresdemploiv2 o2dsoffre",
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def search_france_travail(keywords: str, location: str = "", n: int = 30) -> list[dict]:
    """Fetch live internship offers from France Travail (ex-Pôle Emploi) API.
    Register at https://francetravail.io/data/api/offres-demploi to get free keys.
    Set FT_CLIENT_ID and FT_CLIENT_SECRET in .env.
    """
    if not france_travail_available():
        raise RuntimeError("France Travail keys missing: set FT_CLIENT_ID and FT_CLIENT_SECRET in .env")
    token = _ft_token()
    params: dict = {
        "typeContrat": "ST",  # stage
        "range": f"0-{min(n, 149)}",
    }
    if keywords:
        params["motsCles"] = keywords
    if location:
        params["lieuTravail"] = location
    r = requests.get(
        "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=20,
    )
    r.raise_for_status()
    out = []
    for j in (r.json().get("resultats") or []):
        title = j.get("intitule", "")
        company = (j.get("entreprise") or {}).get("nom", "Unknown company")
        lieu = (j.get("lieuTravail") or {}).get("libelle", "")
        description = _clean(j.get("description", ""))
        link = j.get("origineOffre", {}).get("urlOrigine", "")
        posted = (j.get("dateCreation") or "")[:10]
        out.append({
            "id": "ft-" + _id(title, company, j.get("id", "")),
            "title": title,
            "company": company,
            "location": lieu,
            "description": description,
            "url": link,
            "posted": posted,
            "source": "France Travail",
        })
    return out


def demo_offers() -> list[dict]:
    with open(DATA / "demo_offers.json", encoding="utf-8") as f:
        return json.load(f)


_FR_DATASET_PATH = DATA / "offers_fr.json"
_fr_dataset_cache: list[dict] | None = None


def fr_dataset_available() -> bool:
    return _FR_DATASET_PATH.exists()


def fr_dataset_offers() -> list[dict]:
    """3,100 real French alternance/internship offers (Jan-Jun 2026), built from the
    France-Travail-ML HuggingFace dataset by scripts/build_offers_dataset.py.
    Loaded once and cached in memory (file is ~6 MB)."""
    global _fr_dataset_cache
    if _fr_dataset_cache is None:
        with open(_FR_DATASET_PATH, encoding="utf-8") as f:
            _fr_dataset_cache = json.load(f)
    return _fr_dataset_cache


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
