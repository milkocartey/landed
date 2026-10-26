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

def analyze_offer(description: str) -> dict:
    """
    Scan the offer description against all three lexicon categories.

    Returns:
      {
        "legal":        [{"match": str, "explanation": str, "suggestion": str}, ...],
        "exclusionary": [...],
        "gender_masc":  [stem, ...],  # stems that matched
        "gender_fem":   [stem, ...],
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

    exclusionary = []
    for rule in EXCLUSIONARY:
        m = re.search(rule["pattern"], description, re.IGNORECASE)
        if m:
            exclusionary.append({
                "match": m.group(0),
                "explanation": rule["explanation"],
                "suggestion": rule["suggestion"],
            })

    gender_masc = [
        stem for stem in GENDER_CODED_MASC
        if re.search(r"\b" + stem, description, re.IGNORECASE)
    ]
    gender_fem = [
        stem for stem in GENDER_CODED_FEM
        if re.search(r"\b" + stem, description, re.IGNORECASE)
    ]

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

# Name variants: (male-coded, female-coded, neutral/ambiguous).
# Culturally diverse to test for both gender and origin associations.
_NAME_VARIANTS = [
    ("Alexandre Martin", "Alexandra Martin", "Alex Martin"),
    ("Thomas Dubois", "Théodora Dubois", "T. Dubois"),
    ("Mohammed Belkacem", "Fatima Belkacem", "M. Belkacem"),
    ("Pierre Lefebvre", "Marie Lefebvre", "P. Lefebvre"),
]

_BIAS_THRESHOLD = 3  # points — delta above this triggers "possible_bias"


def counterfactual_test(cv: dict, offer: dict, matcher_module) -> dict:
    """
    Amazon-replay fairness test: re-run the matching score with the candidate
    name swapped across a male / female / gender-neutral triple, keeping every
    other signal identical.

    A score delta > _BIAS_THRESHOLD suggests the embedding encodes cultural
    associations of the name rather than pure skill signals.

    Returns:
      {
        "results":     [{"name": str, "score": int, "semantic": int, "coverage": int}, ...],
        "delta":       int,
        "verdict":     "fair" | "possible_bias",
        "explanation": str,
      }
    """
    base_name: str = cv.get("name", "")

    # Pick the variant set whose first element most closely matches the CV name
    chosen = _NAME_VARIANTS[0]
    first_word = (base_name or "").split()[0].lower()
    for trio in _NAME_VARIANTS:
        if any(n.split()[0].lower() == first_word for n in trio):
            chosen = trio
            break

    results = []
    for name in chosen:
        patched = copy.deepcopy(cv)
        patched["name"] = name

        raw: str = patched.get("raw_text", "")
        if base_name and base_name in raw:
            patched["raw_text"] = raw.replace(base_name, name, 1)
        elif raw:
            patched["raw_text"] = name + "\n" + raw

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
            f"Score delta across {n} name variants: {delta} point(s). "
            "The matching model is not materially influenced by the candidate's apparent name or gender — "
            "this reproduces the Amazon fairness test."
        )
    else:
        best = results[scores.index(max(scores))]["name"]
        worst = results[scores.index(min(scores))]["name"]
        verdict = "possible_bias"
        explanation = (
            f"Score delta across {n} name variants: {delta} point(s) "
            f"(highest: {best} → {max(scores)}, lowest: {worst} → {min(scores)}). "
            f"A delta above {_BIAS_THRESHOLD} suggests the embedding may encode cultural "
            "associations tied to names — the same mechanism that caused Amazon's recruiting AI to "
            "downgrade CVs containing the word 'women's' (Reuters, Oct 2018)."
        )

    return {
        "results": results,
        "delta": delta,
        "verdict": verdict,
        "explanation": explanation,
    }
