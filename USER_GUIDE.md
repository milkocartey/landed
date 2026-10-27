# User guide

### Step 1: Your CV
- Drop a **PDF, DOCX or TXT** CV in the box, or click **Try with Alex Martin's sample CV** (`data/sample_cv.pdf` is also there to test the upload).
- Landed shows the skills it found, grouped by category. Open **See how your CV was read** to check the sections.
- Tip: use a text-based PDF (exported from Word or Google Docs). A scanned image has no readable text.

### Step 2: Matching offers
- Type what you're looking for and where, then **Search**.
  - **Demo offers**: 25 synthetic offers (23 neutral + 2 intentionally biased) so you can try the bias checker immediately.
  - **Vraies offres (France 2026)**: 3,100 real France Travail alternance/internship offers (Jan-Jun 2026), built from an open dataset — see [CREDITS.md](CREDITS.md).
  - **France Travail**: live offers from the France Travail API. Get free keys at https://francetravail.io/data/api and put them in `.env` (`FT_CLIENT_ID`, `FT_CLIENT_SECRET`), then restart.
  - **Live (Adzuna)**: real offers from the Adzuna API. Get free keys at https://developer.adzuna.com/signup and put them in `.env` (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`), then restart.
- **Paste an offer**: found something on JobTeaser, LinkedIn or Welcome to the Jungle? Paste its text. Landed scores it like the others. (We don't scrape these sites: their terms forbid it, and you choose what to bring.)
- Click an offer to see its **match score (0-100)** and its two components:
  - *Meaning of CV and offer*: semantic similarity between your CV and the offer.
  - *Required skills you have*: share of the skills mentioned in the offer that appear in your CV.
- **Write my cover letter and CV**: generates both. On a laptop without GPU it takes about 30-90 seconds.
  - *Cover letter* tab: editable text. A green banner confirms every skill mentioned is in your CV; a yellow one lists skills you never claimed.
  - *Tailored CV* tab: same facts as your CV, with the skills this offer asks for first and your bullet points re-ordered by relevance.
  - Download both as **.docx**, then **Add to board as applied**.
- **Bias check** (below every offer):
  - *Analyse offer wording* — three-layer rule scan:
    1. **Legal risk**: wording potentially discriminatory under French law (Code du travail L.1132-1) — age criteria (*young*, *jeune et dynamique*, explicit age caps), appearance (*bonne présentation*).
    2. **Exclusionary**: *native speaker* / *mother tongue* / *langue maternelle* — excludes highly proficient non-native speakers without adding objectivity. Not illegal per se, but a CEFR level (C1/C2) is a more defensible alternative.
    3. **Gender-coded vocabulary**: counts masculine-signal words (aggressive, competitive, dominant, rockstar…) and feminine-signal words (collaborative, nurturing, empathetic…). Lexicon from Gaucher, Friesen & Kay (2011). Informational — no word is inherently bad, but a strong imbalance can discourage candidates.
  - *Test our score for bias* — **counterfactual fairness test**: the same CV is re-scored three times with a male, a female, and a gender-neutral name. A delta above 3 points flags a potential bias in our own matching model. This reproduces the mechanism behind the Amazon recruiting AI incident (Reuters, Oct 2018), where a model trained on historical CVs learned to downgrade candidates based on name-encoded signals.

### Step 3: Application board
- Drag cards between columns (keyboard: focus a card and press **Alt + ←/→**).
- Click a card to add notes, a contact, the next step and its date.
- Applications sent 10+ days ago without news get a **Follow up** reminder.
- The header shows tracked / sent applications, response rate, interview rate and average match score.

Your data stays in `data/landed.db` (SQLite) and `data/cv.json` on your machine. Delete them to start fresh.

See the main [README](README.md) for how the matching pipeline works, and [INSTALL.md](INSTALL.md) if you haven't set up the app yet.
