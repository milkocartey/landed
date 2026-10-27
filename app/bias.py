"""
Bias analysis for Landed — Phase 3.

Two public functions:
  analyze_offer(description) → wording check across all three lexicon categories
  counterfactual_test(cv, offer, matcher_module) → Amazon-replay fairness test
"""
from __future__ import annotations

import copy
import re

from .bias_lexicon import EXCLUSIONARY, GENDER_CODED_FEM, GENDER_CODED_MASC, LEGAL_RISK


# ---------------------------------------------------------------------------
# 3a — Wording check
# ---------------------------------------------------------------------------

def _dedup_matches(matches: list[dict]) -> list[dict]:
    """Remove dominated matches — if match A's text is a substring of match B's text, drop A."""
    result = []
    for i, m in enumerate(matches):
        dominated = any(
            m["match"].lower() in other["match"].lower() and len(other["match"]) > len(m["match"])
            for j, other in enumerate(matches) if j != i
        )
        if not dominated:
            result.append(m)
    return result


def analyze_offer(description: str) -> dict:
    """
    Scan the offer description against all three lexicon categories.

    Returns:
      {
        "legal":        [{"match": str, "explanation": str, "suggestion": str}, ...],
        "exclusionary": [...],
        "gender_masc":  [word, ...],  # actual words found
        "gender_fem":   [word, ...],
        "gender_note":  str,
      }
    """
    legal = []
    for rule in LEGAL_RISK:
        m = re.search(rule["pattern"], description, re.IGNORECASE)
        if m:
            legal.append({
                "match": m.group(0),
                "explanation": rule["explanation"],
                "suggestion": rule["suggestion"],
            })
    legal = _dedup_matches(legal)

    exclusionary = []
    for rule in EXCLUSIONARY:
        m = re.search(rule["pattern"], description, re.IGNORECASE)
        if m:
            exclusionary.append({
                "match": m.group(0),
                "explanation": rule["explanation"],
                "suggestion": rule["suggestion"],
            })
    exclusionary = _dedup_matches(exclusionary)

    # Return actual words found, not stems
    gender_masc = []
    for stem in GENDER_CODED_MASC:
        m = re.search(r"\b" + stem + r"\w*", description, re.IGNORECASE)
        if m:
            gender_masc.append(m.group(0))

    gender_fem = []
    for stem in GENDER_CODED_FEM:
        m = re.search(r"\b" + stem + r"\w*", description, re.IGNORECASE)
        if m:
            gender_fem.append(m.group(0))

    nm, nf = len(gender_masc), len(gender_fem)
    if nm == 0 and nf == 0:
        note = "Balanced wording: no gender-coded words detected."
    elif nm > nf + 2:
        note = (
            f"Masculine-coded wording ({nm} signal{'s' if nm > 1 else ''} vs {nf}): "
            "statistically associated with male-dominated roles and may discourage some candidates."
        )
    elif nf > nm + 2:
        note = (
            f"Feminine-coded wording ({nf} signal{'s' if nf > 1 else ''} vs {nm}): "
            "statistically associated with female-dominated roles and may discourage some candidates."
        )
    else:
        note = (
            f"Mixed gender coding ({nm} masculine, {nf} feminine signal{'s' if nm + nf > 1 else ''}): "
            "no strong imbalance detected."
        )

    return {
        "legal": legal,
        "exclusionary": exclusionary,
        "gender_masc": gender_masc,
        "gender_fem": gender_fem,
        "gender_note": note,
    }


# ---------------------------------------------------------------------------
# 3b — Counterfactual fairness test (Amazon replay)
# ---------------------------------------------------------------------------

# Six test names: 3 gender pairs × 3 perceived origins (French, Maghrebi, East-Asian).
# Inspired by counterfactual fairness literature (cf. Amazon 2018 incident, Reuters).
# These cover both gender-coding and origin-coding in embeddings.
_TEST_NAMES = [
    ("Thomas Martin",   "M"),  # French-origin, masc
    ("Julie Martin",    "F"),  # French-origin, fem
    ("Mohamed Benali",  "M"),  # Maghrebi-origin, masc
    ("Leïla Benali",    "F"),  # Maghrebi-origin, fem
    ("Kevin Nguyen",    "M"),  # East-Asian-origin, masc
    ("Linh Nguyen",     "F"),  # East-Asian-origin, fem
]

_MASC_PRONOUNS = re.compile(r"\b(he|his|him)\b", re.I)
_FEM_PRONOUNS  = re.compile(r"\b(she|her|hers)\b", re.I)

_BIAS_THRESHOLD = 3  # points — delta above this triggers "possible_bias"


def _swap_pronouns(text: str, to_gender: str) -> str:
    """Replace gendered pronouns when swapping to a different gender."""
    if to_gender == "F":
        return _MASC_PRONOUNS.sub(lambda m: {"he": "she", "his": "her", "him": "her"}[m.group(0).lower()], text)
    return _FEM_PRONOUNS.sub(lambda m: {"she": "he", "her": "his", "hers": "his"}[m.group(0).lower()], text)


def counterfactual_test(cv: dict, offer: dict, matcher_module) -> dict:
    """
    Counterfactual fairness test: re-run matching with 6 name variants covering
    gender and perceived ethnic origin, keeping every other signal identical.

    Inspired by the mechanism that caused Amazon's recruiting AI to downgrade
    CVs containing the word 'women's' (Reuters, Oct 2018), but does NOT claim
    to replicate that specific experiment.

    A score delta > _BIAS_THRESHOLD suggests the embedding may encode cultural
    associations beyond pure skill signals.

    Returns:
      {
        "results":     [{"name": str, "score": int, "semantic": int, "coverage": int}, ...],
        "delta":       int,
        "verdict":     "fair" | "possible_bias",
        "explanation": str,
      }
    """
    base_name: str = cv.get("name", "")
    base_raw: str = cv.get("raw_text", "")

    results = []
    for name, gender in _TEST_NAMES:
        patched = copy.deepcopy(cv)
        patched["name"] = name

        raw = base_raw
        if base_name and base_name in raw:
            raw = raw.replace(base_name, name)  # replace ALL occurrences
        elif raw:
            raw = name + "\n" + raw

        raw = _swap_pronouns(raw, gender)
        patched["raw_text"] = raw

        ranked = matcher_module.rank_offers(
            patched["raw_text"],
            patched.get("skills", []),
            [offer],
        )
        r = ranked[0]
        results.append({
            "name": name,
            "score": r["score"],
            "semantic": r["semantic"],
            "coverage": r["coverage"],
        })

    scores = [r["score"] for r in results]
    delta = max(scores) - min(scores)
    n = len(results)

    if delta <= _BIAS_THRESHOLD:
        verdict = "fair"
        explanation = (
            f"Score delta across {n} name variants (3 gender pairs, 3 origins): {delta} point(s). "
            "The matching model shows no material sensitivity to the candidate's apparent name, "
            "gender, or ethnic origin — a good signal for algorithmic fairness."
        )
    else:
        best = results[scores.index(max(scores))]["name"]
        worst = results[scores.index(min(scores))]["name"]
        verdict = "possible_bias"
        explanation = (
            f"Score delta across {n} name variants: {delta} point(s) "
            f"(highest: {best} → {max(scores)}, lowest: {worst} → {min(scores)}). "
            f"A delta above {_BIAS_THRESHOLD} points suggests the embedding may encode cultural "
            "associations beyond pure skill signals. "
            "This does not definitively prove discrimination — it is a signal worth investigating."
        )

    return {
        "results": results,
        "delta": delta,
        "verdict": verdict,
        "explanation": explanation,
    }
