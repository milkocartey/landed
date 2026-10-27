# CHANGES — branch fix/review-oct27 (2026-10-27)

Nine numbered fixes applied autonomously.

---

## Item 1 — Fix generation hang on CPU

**Files:** `app/generator.py`, `app/main.py`

- `_hf_generate`: switched from sampling (`do_sample=True, temperature=0.6`) to greedy decoding (`do_sample=False`). ~2× faster on CPU.
- `cover_letter()`: reduced `max_new_tokens` from 520 → 300; trimmed CV input to `_cv_for_prompt(cv, 800)` (summary + top experience only) and offer description to 500 chars. Total LLM input dropped from ~4 500 to ~1 300 chars.
- `tailor_cv()`: same prompt trimming; `max_new_tokens` 120 → 80 for the profile summary.
- Added `_cv_for_prompt()` helper: extracts name + summary + top experience bullets (capped at `max_chars`).
- Added `_template_cv()`: algorithmic CV tailoring without any LLM call, used as timeout fallback.
- `/api/generate` route: converted to `async def` with `asyncio.wait_for(run_in_threadpool(...), timeout=90.0)`. On 90-second timeout, returns template CV + template letter immediately instead of leaving the spinner forever.

**Decision:** 90 s timeout is generous for a 1.5B model on CPU; most runs finish in 30–60 s with greedy. The template fallback preserves UX on slower machines.

---

## Item 2 — Paste-offer form (already functional)

**Files:** none

Audited `static/index.html`, `static/app.js` and `app/main.py`. All required elements (`#paste-form`, `#m-title`, `#m-company`, `#m-desc`, `#m-url`, `#m-source`) exist in the HTML; the JS listener is wired; `/api/offers/manual` exists in the backend. The form is visible in the right detail panel before any offer is selected.

Null-checks for `#paste-inline` were already in place from a previous session. No changes needed.

---

## Item 3 — Bias flags visible in offer cards

**Files:** `app/main.py`, `static/app.js`, `static/styles.css`

- `/api/offers/search` and `/api/offers/manual`: runs `analyze_offer()` on each ranked offer; adds `flags_count` (legal + exclusionary count) and `flags_legal` (legal-only count) to every offer object.
- `renderOffers()`: shows `⚠ N flags` amber badge on each card with `flags_count > 0`. Badge title distinguishes legal vs. exclusionary.
- `renderDetail()`: the "nothing missing" message is now cautious when `(matched + missing) < 4` skills detected: *"Only N skills detected — paste the full offer description for a more accurate analysis."*

---

## Item 4 — Fairness test improved

**Files:** `app/bias.py`

- Extended from 3 name variants (one trio) to **6 names covering 3 gender pairs × 3 perceived origins**: Thomas/Julie Martin (French), Mohamed/Leïla Benali (Maghrebi), Kevin/Linh Nguyen (East-Asian).
- Test always runs all 6 names regardless of the user's own name.
- **All occurrences** of the base name are now replaced (was `.replace(name, n, 1)`).
- Added `_swap_pronouns()`: when swapping to a female name, replaces he/his/him → she/her/her in the CV text, and vice versa.
- Removed "this reproduces the Amazon fairness test" overclaim; replaced with honest framing: *"inspired by the mechanism… does not definitively prove discrimination."*
- Updated JS loader text to "Testing 6 name variants (3 gender pairs, 3 origins)…"

---

## Item 5 — Red flag report accuracy

**Files:** `app/bias.py`, `app/bias_lexicon.py`, `app/CREDITS.md`

- **Legal article corrected**: all references to `L.1133-1` as the *prohibition* changed to `L.1132-1`. L.1132-1 is the general non-discrimination principle; L.1133-1 is the exception (essential professional requirement). Fixed in lexicon strings and CREDITS.md.
- **Deduplication**: added `_dedup_matches()`. If pattern A's matched text is a strict substring of pattern B's matched text, A is dropped. E.g. "young" is no longer reported alongside "young professional" in the same phrase.
- **Actual words not stems**: gender-coded word detection now uses `re.search(r"\b" + stem + r"\w*", ...)` and appends the full matched word (e.g. "competitive" instead of "competi").

---

## Item 6 — CV skill extraction improved

**Files:** `app/skills.py`, `app/cv_parser.py`

**skills.py:**
- Removed `"audit"` from `Accounting` aliases — it was a false positive when a cybersecurity CV mentioned "security audit". Replaced with `"financial audit"` and `"audit comptable"`.
- Added **KPI** skill: `("Business", ["kpi", "kpis", "key performance indicators?"])`.
- Added **Negotiation** skill: `("Business", [r"\bnegotiat(?:ion|ing|e)\b", ...])`.
- Added `"b2b"` and `"b-to-b"` to Business Development aliases (standalone B2B now extracted, in addition to "b2b sales" in Sales).

**cv_parser.py:**
- Fixed `_heading_key()`: now lowercases the line *before* the regex, so uppercase accented characters (É, È, etc.) are handled correctly. Also replaces any non-alphabetic character (including `&`, `/`, `–`) with a space, then collapses multiple spaces.
- Added to SECTION_HEADINGS:
  - `skills`: "skills tools", "skills and tools", "compétences outils", "certifications"
  - `languages`: "langues et certifications", "languages and certifications", "langues certifications"
  - `activities`: "activités", "activités extrascolaires", "engagements"
  - `education`: "formations", "diplômes"
  - `experience`: "professional experiences", "expérience"

---

## Item 7 — Search bugs fixed

**Files:** `app/main.py`

- **Location filter**: added accent-insensitive, case-insensitive location matching (`_norm()` strips NFD combining chars). Offers are filtered by location when a location is provided; if no offer matches the location, the full unfiltered list is kept (to avoid empty results on typos).
- **Empty keyword state**: removed the `or offers` fallback — if keywords match nothing, an empty list is returned. The frontend already shows "No results. Try different keywords…" in this case.
- Adzuna toggle was already hidden when no API key is configured (done in a previous session); verified no change needed.

---

## Item 8 — Board layout at narrow widths

**Files:** `static/styles.css`, `static/app.js`

- `.board-cols-wrap`: added `overflow-x: auto; -webkit-overflow-scrolling: touch`. Changed `.board` to `min-width: 800px` with `minmax(200px, 1fr)` columns, so the board scrolls horizontally on small screens instead of collapsing.
- `cardHTML()`: each board card now has a `<select class="card-status-select">` that lists all statuses. Selecting one calls `moveCard()` directly. Prevents the need to drag on mobile.
- Added board `change` event listener: intercepts `card-status-select` changes and moves the card without opening the editor.
- Fixed two stale `loadBoard(false)` calls → `loadBoard()`.

---

## Item 9 — Tests

**Files:** `tests/test_skills.py`, `tests/test_cv_parser.py`, `tests/test_bias.py`, `tests/test_search.py`

26 pytest tests covering:
- Skill extraction: Accounting false positive, KPI, Negotiation, B2B, CRM, LinkedIn, Go-to-market
- CV parser: "SKILLS & TOOLS", "CERTIFICATIONS", "COMPÉTENCES & OUTILS" heading detection
- Bias: dedup, actual words (not stems), 6-name fairness test, clean offer produces no flags
- Search: location filter (Paris, accent-insensitive), empty keyword state, flags_count on all offers, manual offer endpoint

All 26 pass: `pytest tests/ -q` → 26 passed.

---

## Legal reference correction note

The original code (and CREDITS.md) cited **L.1133-1** as the French article prohibiting discrimination. This is incorrect:
- **L.1132-1** = general prohibition of discrimination in hiring
- **L.1133-1** = exception allowing a criterion when it is an "essential and determining professional requirement"

All six occurrences in `bias_lexicon.py` and the one in `CREDITS.md` have been corrected.
