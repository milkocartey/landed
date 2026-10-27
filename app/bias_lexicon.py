"""
Bias lexicon for Landed — offer wording analysis.

Three categories:

LEGAL_RISK
  Wording that may be discriminatory under French law (Code du travail L.1132-1),
  which prohibits hiring discrimination based on age, sex, origin, appearance, etc.
  (L.1133-1 is the exception that allows it when the criterion is an essential and
  determining professional requirement).

EXCLUSIONARY
  Wording that is not illegal per se but tends to exclude qualified candidates
  without a legitimate justification (e.g. language-level requirements stated
  as "native speaker" rather than a measurable proficiency level).

GENDER_CODED_MASC / GENDER_CODED_FEM
  Words statistically associated with male-dominated or female-dominated jobs.
  Informational only — no wording is inherently bad, but a strong imbalance
  may discourage candidates of one gender from applying.
  Source: Gaucher, Friesen & Kay (2011). Evidence That Gendered Wording in Job
  Advertisements Exists and Sustains Gender Inequality. Journal of Personality
  and Social Psychology, 101(1), 109-128.

Additional reference:
  Reuters (Oct 2018). Amazon scraps secret AI recruiting tool that showed bias
  against women. https://www.reuters.com/article/us-amazon-com-jobs-automation-insight
  Illustrates how an AI trained on past CVs (mostly from men) learned to
  downgrade CVs containing the word "women's" — a classic example of
  historical-bias amplification that our counterfactual test is designed to detect.
"""

# Each entry: pattern (regex, case-insensitive), explanation, suggestion.
LEGAL_RISK = [
    {
        "pattern": r"\byoung(?:\s+and\s+dynamic)?\b",
        "explanation": (
            "Age criteria in job ads are illegal in France (Code du travail L.1132-1) "
            "unless the role has an essential and determining age requirement (exception: L.1133-1). "
            "'Young' implies an age preference."
        ),
        "suggestion": "Remove the age reference. Describe the seniority level instead (e.g. 'entry-level', 'junior').",
    },
    {
        "pattern": r"\byoung\s+professional\b",
        "explanation": (
            "Targeting 'young professionals' implies an age preference, which is "
            "discriminatory under French law (Code du travail L.1132-1)."
        ),
        "suggestion": "Use 'early-career professional' or specify the number of years of experience.",
    },
    {
        "pattern": r"\bjeune\s+et\s+dynamique\b",
        "explanation": (
            "Critère d'âge implicite : l'expression 'jeune et dynamique' cible un groupe "
            "d'âge, ce qui est interdit par le Code du travail (L.1132-1)."
        ),
        "suggestion": "Supprimer la référence à l'âge. Utiliser uniquement 'dynamique' ou décrire le rythme de travail.",
    },
    {
        "pattern": r"\bjeune\b",
        "explanation": (
            "Critère d'âge : cibler un candidat 'jeune' est interdit en France "
            "(Code du travail L.1132-1) sauf si l'âge est une exigence professionnelle déterminante (L.1133-1)."
        ),
        "suggestion": "Décrire le niveau d'expérience souhaité (ex. : 'débutant accepté', 'junior').",
    },
    {
        "pattern": r"\bmax(?:imum)?\s*\d+\s*(?:years?|ans?)\b",
        "explanation": "Explicit age cap is discriminatory and illegal in France (Code du travail L.1132-1).",
        "suggestion": "Remove the age limit entirely.",
    },
    {
        "pattern": r"\bgood\s+presentation\b",
        "explanation": (
            "Appearance-based criteria are illegal in France (Code du travail L.1132-1) "
            "unless the role strictly requires it (e.g. uniformed security)."
        ),
        "suggestion": "Specify what the role actually requires (e.g. 'client-facing role', 'professional attire required').",
    },
    {
        "pattern": r"\bbonne\s+pr[eé]sentation\b",
        "explanation": (
            "Critère d'apparence physique : illégal en France (Code du travail L.1132-1) "
            "sauf si justifié par la nature essentielle du poste."
        ),
        "suggestion": "Préciser ce que le poste implique réellement (ex. : 'poste en contact direct avec la clientèle').",
    },
    {
        "pattern": r"\bpr[eé]sentable\b",
        "explanation": (
            "Critère d'apparence physique implicite, potentiellement illégal (Code du travail L.1132-1)."
        ),
        "suggestion": "Préciser les exigences réelles du poste.",
    },
]

# Not illegal, but worth flagging with a nuanced explanation.
EXCLUSIONARY = [
    {
        "pattern": r"\bnative\s+speaker\b",
        "explanation": (
            "Requiring a 'native speaker' can exclude highly proficient non-native speakers "
            "who meet every practical need of the role. A language level (e.g. C1 or C2) "
            "is a more objective and legally defensible criterion. "
            "Note: this is not illegal per se — a language requirement can be legitimate."
        ),
        "suggestion": "Specify the required level: 'fluent (C1 or above)' or 'business proficiency (C1)'.",
    },
    {
        "pattern": r"\bmother\s+tongue\b",
        "explanation": (
            "Same issue as 'native speaker': it excludes proficient non-native speakers. "
            "Note: not illegal per se when a high language level is genuinely required."
        ),
        "suggestion": "Use a proficiency level: 'fluent (C1 or above)' or 'near-native (C2)'.",
    },
    {
        "pattern": r"\blangue\s+maternelle\b",
        "explanation": (
            "Exiger la 'langue maternelle' peut exclure des candidats très compétents non natifs. "
            "Un niveau certifié (ex. C1) est plus objectif. "
            "Note : l'exigence linguistique n'est pas illégale en soi si elle est justifiée."
        ),
        "suggestion": "Préciser le niveau requis : 'courant (niveau C1 minimum)' ou 'bilingue (C2)'.",
    },
]

# Source: Gaucher, Friesen & Kay (2011), J. Personality & Social Psychology 101(1), 109-128.
# Each entry is a regex stem matched with re.search(r'\b' + stem, text, re.I).
GENDER_CODED_MASC = [
    "competi",      # competitive, competition
    "dominan",      # dominant, dominance
    "aggress",      # aggressive, aggression
    "fearless",
    "independen",   # independent, independence
    "individual",
    "rockstar",
    "ninja",
    "champion",
    "superior",
    "confiden",     # confident, confidence
    "decisi",       # decisive, decision-maker
    "outperform",
    "driven",
    "asserti",      # assertive, assertiveness
    "bold",
    "lead",         # leader, leadership
    "challeng",     # challenge, challenging
    "ambitio",      # ambitious, ambition
]

GENDER_CODED_FEM = [
    "collaborati",  # collaborative, collaboration
    "cooperati",    # cooperative, cooperation
    "support",
    "nurtur",       # nurturing, nurture
    "compassion",
    "interpersonal",
    "commit",       # committed, commitment
    "empath",       # empathy, empathetic
    "sensitiv",     # sensitive, sensitivity
    "caring",
    "warm",
    "honest",
    "trust",
    "inclusive",
    "understandin", # understanding
    "kind",
]
