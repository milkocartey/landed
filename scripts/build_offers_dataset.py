"""Build data/offers_fr.json from the France-Travail-ML HuggingFace dataset.

Usage
-----
    python scripts/build_offers_dataset.py           # step 1: report stats, then exit
    python scripts/build_offers_dataset.py --build   # step 2: build + save offers_fr.json

The script downloads the Parquet file once and caches it at
data/_hf_cache/offres_emplois.parquet so repeated runs are instant.

Dataset: France-Travail-ML/Offres-Emplois-JAN-26-JUIN-26-RAW
License: Apache-2.0 (declared by uploader; provenance not independently verified)
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE_DIR = DATA / "_hf_cache"
OUT_PATH = DATA / "offers_fr.json"

REPO_ID = "France-Travail-ML/Offres-Emplois-JAN-26-JUIN-26-RAW"
PARQUET_FILES = [
    "train-00000-of-00002.parquet",
    "train-00001-of-00002.parquet",
]
PARQUET_PATHS = [CACHE_DIR / f for f in PARQUET_FILES]

# ------------------------------------------------------------------ helpers
def _download_parquet() -> list[Path]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    from huggingface_hub import hf_hub_download
    downloaded = []
    for fname, dest in zip(PARQUET_FILES, PARQUET_PATHS):
        if dest.exists():
            size_mb = dest.stat().st_size / 1024 / 1024
            print(f"[cache] {dest.name} already exists ({size_mb:.0f} MB) — skipping.")
            downloaded.append(dest)
            continue
        print(f"[download] Fetching {fname} from {REPO_ID} …")
        hf_hub_download(
            repo_id=REPO_ID,
            repo_type="dataset",
            filename=fname,
            local_dir=str(CACHE_DIR),
        )
        size_mb = dest.stat().st_size / 1024 / 1024
        print(f"[download] Done — {size_mb:.0f} MB → {dest}")
        downloaded.append(dest)
    return downloaded


def _load_table():
    import pyarrow as pa
    import pyarrow.parquet as pq
    tables = [pq.read_table(str(p)) for p in PARQUET_PATHS if p.exists()]
    if not tables:
        raise RuntimeError("No parquet files found in cache")
    return pa.concat_tables(tables) if len(tables) > 1 else tables[0]


def _get(row: dict, *keys: str, default: str = "") -> str:
    """Column accessor — handles both flat dotted keys ('entreprise.nom')
    and nested dicts transparently."""
    # Try flat dotted key first (this dataset uses flat column names)
    flat = ".".join(keys)
    if flat in row:
        v = row[flat]
        return (v or default) if isinstance(v, str) else default
    # Fall back to nested traversal for other datasets
    v = row
    for k in keys:
        if not isinstance(v, dict):
            return default
        v = v.get(k, default)
    return (v or default) if isinstance(v, str) else default


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# ------------------------------------------------------------------ step 1: report
def report(table) -> None:
    total = len(table)
    print(f"\n{'='*60}")
    print(f" Dataset: {REPO_ID}")
    print(f" Total rows: {total:,}")
    print(f"{'='*60}\n")

    rows = table.to_pylist()

    # contract type distribution
    type_counter: Counter = Counter()
    for r in rows:
        t = _get(r, "typeContratLibelle") or "—"
        type_counter[t] += 1
    print("typeContratLibelle distribution (top 15):")
    for label, count in type_counter.most_common(15):
        pct = 100 * count / total
        print(f"  {count:>7,}  {pct:5.1f}%  {label}")

    # alternance count
    alt_count = sum(1 for r in rows if r.get("alternance") is True)
    print(f"\nalternance == True: {alt_count:,}  ({100*alt_count/total:.1f}%)")

    # internship keyword filter
    STAGE_RE = re.compile(
        r"\b(stage|stagiaire|internship|intern|alternance|apprentissage)\b",
        re.I,
    )
    stage_rows = [
        r for r in rows
        if STAGE_RE.search(_get(r, "intitule")) or STAGE_RE.search(_get(r, "description"))
    ]
    print(f"\nRows with stage/stagiaire/internship/alternance in intitule or description:")
    print(f"  {len(stage_rows):,}  ({100*len(stage_rows)/total:.1f}%)")

    # 5 examples from stage_rows
    print("\n--- 5 examples ---")
    for r in stage_rows[:5]:
        intitule = _get(r, "intitule")
        company = _get(r, "entreprise", "nom") or "—"
        location = _get(r, "lieuTravail", "libelle") or "—"
        contract = _get(r, "typeContratLibelle") or "—"
        alt = r.get("alternance", False)
        desc_snippet = _clean_html(_get(r, "description"))[:120]
        print(f"  [{contract}{'  ALT' if alt else ''}] {intitule}")
        print(f"    {company} | {location}")
        print(f"    {desc_snippet}…")
        print()


# ------------------------------------------------------------------ step 2: build
ALT_MARKER_RE = re.compile(
    r"\b(alternance|apprenti|stage|stagiaire|intern)\b",
    re.I,
)
BIZ_TITLE_RE = re.compile(
    r"\b(marketing|financ|comptab|audit|conseil|consultant|strateg|"
    r"analyst[e]?|communication|digital|"
    r"charg[eé][e]? de (comm|mark|rh|projet|business)|"
    r"ressources humaines|supply chain|logistiq|achat[s]?|"
    r"chef de projet|data analyst|business develop|business intellig|"
    r"contr[oô]l(eur|e de gestion)|commercial[e]?|gestion de projet|"
    r"international|juridique|management)\b",
    re.I,
)
# Exclude hyper-specific trades that happen to use business words
EXCLUDE_TITLE_RE = re.compile(
    r"\b(automobile|assurance|boulang|pâtissier|agricul|viticul|"
    r"vétérin|pharmacie|médical|infirmier|aide[- ]soignant|"
    r"immobilier|notaire|expert[- ]comptable indépendant)\b",
    re.I,
)

MAX_OFFERS = 3_100  # take all clean rows (expected ~3,042)


def _keep(r: dict) -> bool:
    """Return True if this row is a business-school-relevant alternance offer."""
    intitule = _get(r, "intitule")
    description = _get(r, "description")
    alt = r.get("alternance") is True

    # Must have alternance flag OR alternance/stage keyword in title
    if not alt and not ALT_MARKER_RE.search(intitule):
        return False
    # Must have a business-school function keyword in the title
    if not BIZ_TITLE_RE.search(intitule):
        return False
    # Exclude hyper-specific trades in the title
    if EXCLUDE_TITLE_RE.search(intitule):
        return False
    # Must have some description content
    if len(description.strip()) < 80:
        return False
    return True


def _to_offer(r: dict) -> dict:
    rid = str(r.get("id") or "")
    if not rid:
        import hashlib
        rid = hashlib.sha1((_get(r, "intitule") + _get(r, "entreprise.nom")).encode()).hexdigest()[:12]
    return {
        "id": "ft-" + rid,
        "title": _get(r, "intitule"),
        "company": _get(r, "entreprise.nom") or "Unknown company",
        "location": _get(r, "lieuTravail.libelle"),
        "description": _clean_html(_get(r, "description")),
        "url": _get(r, "origineOffre.urlOrigine"),
        "posted": (_get(r, "dateCreation") or "")[:10],
        "source": "France Travail dataset (HF)",
    }


def build(table) -> None:
    rows = table.to_pylist()
    kept = [r for r in rows if _keep(r)]
    print(f"\n[build] {len(kept):,} rows pass the filter (cap: {MAX_OFFERS:,})")

    # sample evenly if over cap
    if len(kept) > MAX_OFFERS:
        import random
        random.seed(42)
        kept = random.sample(kept, MAX_OFFERS)
        print(f"[build] Sampled down to {len(kept):,}")

    offers = [_to_offer(r) for r in kept]

    # deduplicate by id
    seen: set[str] = set()
    unique = []
    for o in offers:
        if o["id"] not in seen:
            seen.add(o["id"])
            unique.append(o)
    print(f"[build] {len(unique):,} unique offers after dedup")

    OUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=1)
    print(f"[build] Saved → {OUT_PATH}  ({OUT_PATH.stat().st_size / 1024:.0f} KB)")

    # quick bias scan
    try:
        sys.path.insert(0, str(ROOT))
        from app.bias import analyze_offer
        flag_counter: Counter = Counter()
        flagged = 0
        for o in unique:
            r = analyze_offer(o["description"])
            n = len(r["legal"]) + len(r["exclusionary"])
            if n:
                flagged += 1
                for f in r["legal"]:
                    flag_counter["legal: " + f["match"][:40]] += 1
                for f in r["exclusionary"]:
                    flag_counter["excl: " + f["match"][:40]] += 1
        print(f"\n[bias] {flagged}/{len(unique)} offers flagged ({100*flagged/len(unique):.1f}%)")
        print("[bias] Top 10 flags:")
        for match, cnt in flag_counter.most_common(10):
            print(f"  {cnt:>4}×  {match}")
    except Exception as e:
        print(f"[bias] Skipped (app not importable from here): {e}")


# ------------------------------------------------------------------ main
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true",
                        help="After reporting stats, build and save offers_fr.json")
    args = parser.parse_args()

    _download_parquet()
    print("[load] Reading parquet …")
    table = _load_table()

    report(table)

    if args.build:
        build(table)
    else:
        print("\n--- Stats printed above. ---")
        print("Run with --build once you're happy with the filter.")


if __name__ == "__main__":
    main()
