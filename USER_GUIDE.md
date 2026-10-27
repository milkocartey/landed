# Landed — User Guide

**Landed** is an open-source AI assistant for internship applications. You give it your CV and a job offer; it gives you a match score, the skills you are missing, a bias check of the offer and of our own model, and a first draft of a tailored cover letter and CV. A board lets you track every application.

Everything runs **locally on your computer** with open-source models from Hugging Face. No paid API, no account, and your CV is not sent to any chatbot.

> AAA (Advanced AI Algorithms) — Group 42: Charline Richard, Claire Shelby, Milo Carteyrade, Saoussen Zouari.

---

## 1. Installation

### Requirements
- **Python 3.10 or newer** (check with `python3 --version`, or `python --version` on Windows).
- **Disk space:** plan for about **5 GB** free (measured: ~1.2 GB for the Python virtual environment and dependencies, ~3 GB for the two Hugging Face models).
- **Internet** for the first launch only (dependencies and model downloads). After that, the app works offline.
- A GPU is **not** required.

### Start the app

1. Download the project from https://github.com/milkocartey/landed (green **Code** button → **Download ZIP**) and unzip it. Full step-by-step instructions are in `INSTALL.md`.
2. Open a terminal **in the project folder**.
3. Run:

| System | Command |
|---|---|
| macOS / Linux | `./run.sh` |
| Windows | double-click `run.bat`, or run `run.bat` in a terminal |

The first launch creates a virtual environment and installs the dependencies (a few minutes). Then open **http://localhost:8000** in your browser.

To stop the app, go back to the terminal and press `Ctrl + C`. To restart it, run the same command again (it is much faster the second time).

<details>
<summary>Manual installation (if the script does not work)</summary>

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
python -m app.main
```
</details>

### First use: model downloads
The first time you match an offer and write a letter, Landed downloads two open-source models from Hugging Face:
- **Matcher:** `sentence-transformers/all-MiniLM-L6-v2` (about 90 MB).
- **Writer:** `Qwen/Qwen2.5-1.5B-Instruct` (about 3 GB).

This happens once; they are then cached on your computer.

### Which engine is running?
The **coloured dot in the top bar** shows which engines are active:
- **Green:** AI models (semantic matching + LLM writer).
- **Yellow:** fallback mode (TF-IDF matching + template letters). This happens if the models are not installed or could not load. The app still works, with simpler results.

---

## 2. Using Landed, step by step

### Step 1 — Your CV
- **Upload** a PDF, DOCX or TXT file, **or paste** the text of your CV.
- No CV at hand? Click the **sample CV** button (fictional candidate "Alex Martin"). `data/sample_cv.pdf` is also provided to test the upload.
- Landed lists the skills it found, grouped by category. Open **"See how your CV was read"** to check which sections were recognised.

**Tip:** use a text-based PDF (exported from Word or Google Docs). A scanned image contains no readable text.

### Step 2 — The offer
Two ways to get an offer:
- **Paste an offer** (title, company, description). This is the recommended way for offers found on JobTeaser, LinkedIn, Welcome to the Jungle, etc. Landed does not scrape these sites: their terms of use forbid it.
- **Search** the offers shipped with the app, by keyword and location. Four sources, selected with the buttons above the search box:
  - **Demo offers**: 25 synthetic offers with fictional companies (23 neutral + 2 intentionally biased), so you can try the bias checker immediately.
  - **Vraies offres (France 2026)**: 3,100 real offers selected from a public Hugging Face dataset of French job ads, January–June 2026 (France Travail schema). The dataset has no dedicated recruiter-contact field, but a handful of offers still have an email or phone number inside the free-text description, copied as-is from the original posting — see `CREDITS.md` for the dataset's exact provenance and limits.
  - **France Travail**: live offers from the France Travail API. Needs free keys in `.env` (`FT_CLIENT_ID`, `FT_CLIENT_SECRET`) — see section 4. Greyed out until then.
  - **Adzuna**: live offers from the Adzuna API. Needs free keys in `.env` (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`) — see section 4. Greyed out until then. *(We could not re-verify live results from this source without a personal API key; the button and request code are in place, but end-to-end behaviour with real keys hasn't been re-tested recently.)*

### Step 3 — Match result
Click an offer to see:
- **Match score (0–100)**, made of two components:
  - **Meaning of CV and offer:** semantic similarity between the two texts, computed with sentence embeddings.
  - **Required skills you have:** share of the skills mentioned in the offer that also appear in your CV.
- **Skills you have** and **skills you are missing** for this offer.

The score is a reading aid, not a verdict. A low score can still be worth an application if you can explain the gap.

### Step 4 — Bias check
Landed checks two things.

**a. Wording of the job offer** (rule-based, works on English and French offers). Flagged phrases are highlighted, each with a short explanation and a suggested alternative:
- **Legal risk:** e.g. age-related wording ("young and dynamic", "jeune et dynamique"), or appearance criteria ("bonne présentation"). In France, these are discriminatory under the Code du travail (art. L1132-1), except where the criterion is an essential and determining professional requirement (exception: L1133-1).
- **Possibly exclusionary:** e.g. "native speaker", "langue maternelle". A language level can be a legitimate requirement; "fluent" or "C1 level" is the inclusive alternative.
- **Gender-coded words** (information only): balance of masculine-coded words ("competitive", "dominant"…) and feminine-coded words ("supportive", "collaborative"…), based on Gaucher, Friesen & Kay (2011).

This check is **not legal advice**.

**b. "Test our score for bias"** — a counterfactual fairness test of our own matching model, inspired by (but not a literal replay of) the Amazon recruiting AI case, where a model trained on past hires learned to penalise CVs with certain name-encoded signals (Reuters, Oct 2018). It runs on **copies** of your CV; your CV is never modified:
- Your CV is re-scored against the same offer with **6 name variants**: 3 gender pairs (male/female) across 3 perceived origins (French, Maghrebi, East-Asian-coded names), with pronouns swapped to match.
- The table shows each variant's score. A delta above 3 points between the highest and lowest score flags a potential bias in our own model; below that, the model shows no material sensitivity to the name signals tested.
- This does not prove the model is fair in general — only that it isn't sensitive to the specific name/origin signals in this test.

Results are computed live, never hard-coded.

### Step 5 — Cover letter and tailored CV
Click **"Write my cover letter and CV"**. On a laptop without a GPU this takes from several seconds to about 90 seconds, depending on the machine.

- **Cover letter:** editable text. A **green banner** confirms that every skill mentioned is in your CV; a **yellow banner** lists skills the letter mentions but you never claimed (hallucination guard). Fix or remove those before sending.
- **Tailored CV:** your CV reordered to highlight what matters for this offer, using only facts from your original CV.
- **Export** both as **.docx** files.

Always reread before sending: this is a first draft.

### Step 6 — Application board
Save an offer to the board and follow it through the stages: **saved → applied → interview → offer / rejected**.
- Move a card by **drag and drop** or the keyboard (focus a card, press **Alt + ←/→**), or with the **status menu** on the card (useful on mobile).
- Click a card to add notes, a contact, the next step and its date.
- Applications sent 10+ days ago without news get a **Follow up** reminder.
- The header shows tracked / sent applications, response rate, interview rate and average match score.

---

## 3. Your data

- Everything stays on your computer. Your CV and your board are stored in the `data/` folder (`data/cv.json`, `data/landed.db`).
- **To reset the app** (new CV, empty board): stop the app, delete these two files, restart.
- The app is designed for **one user on their own computer**. Do not put it online as is: every visitor would see the same CV and board.

---

## 4. Optional settings (`.env`)

The `.env` file (created from `.env.example` on first launch) lets you change engines. Restart the app after editing it.

| Setting | Values | Effect |
|---|---|---|
| `LANDED_EMBEDDINGS` | `auto` / `tfidf` | `tfidf` = light matching, no model download |
| `LANDED_LLM` | `auto` / `transformers` / `ollama` / `template` | `template` = no LLM, template letters |
| `LANDED_HF_MODEL` | Hugging Face model id | Writing model (default `Qwen/Qwen2.5-1.5B-Instruct`) |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | free keys from developer.adzuna.com | Enables the "Adzuna" live offer source |
| `FT_CLIENT_ID`, `FT_CLIENT_SECRET` | free keys from francetravail.io/data/api | Enables the "France Travail" live offer source |
| `PORT` | default `8000` | Change if port 8000 is already used |

`.env.example` currently lists the Adzuna keys only — add the two `FT_` lines yourself to enable the France Travail live source.

**Light mode** (slow or small computer): set `LANDED_EMBEDDINGS=tfidf` and `LANDED_LLM=template`. No model download, but simpler matching and letters.

---

## 5. Troubleshooting

| Problem | Fix |
|---|---|
| `python: command not found` | Install Python 3.10+ from python.org (on Windows, tick "Add Python to PATH"). |
| `./run.sh: Permission denied` (macOS/Linux) | Run `chmod +x run.sh` once, then `./run.sh`. |
| Page does not load | Check the terminal is still running and shows no error, then reload http://localhost:8000. |
| "Address already in use" | Another program uses port 8000: change `PORT` in `.env` and open the new address. |
| Yellow dot in the top bar | The AI models did not load (no internet at first launch, or not enough disk/RAM). Check the terminal message, or keep using the fallback mode. |
| Letter generation is very slow | Normal on CPU for the first run. Close other heavy apps, or switch to light mode. |
| No skills found in my CV | Your PDF is probably a scanned image. Export a text PDF, or paste the text. |

See `INSTALL.md` for more troubleshooting entries (Python PATH issues, venv errors, port conflicts in detail, etc.).

---

## 6. Limits

- The match score measures text similarity and skill overlap; it does not know the recruiter's real priorities.
- The skill extractor uses a fixed list of skills and aliases: rare or very specific skills may be missed.
- The bias wording check is rule-based: it can miss biased phrasing that is not in its lexicon, and it is not legal advice.
- A small local LLM can make mistakes. The hallucination guard checks skills, not every sentence: always reread the letter.
- Demo offers are synthetic. The real offers ("Vraies offres (France 2026)") are a fixed snapshot (January–June 2026) from a third-party dataset whose provenance is not independently verified; they are not updated.

Credits (models, packages, datasets, references) are listed in `CREDITS.md`. The prompts used with Claude (Anthropic) during development are in `prompts_log.md`.
