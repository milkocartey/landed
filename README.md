# Landed ✈ — from CV to internship, on one board

**Landed** is an open-source AI assistant for the internship hunt. You drop your CV, and it:

1. **Reads your CV** and extracts your skills, experiences and projects.
2. **Ranks internship offers** by how well they fit you, and explains why (skills you have, skills the offer also asks for).
3. **Writes a tailored cover letter and CV version** for each offer, using only facts from your CV, and **flags any skill you never claimed**.
4. **Tracks every application** on a departures-style board (saved → applied → interview → offer / rejected), with follow-up reminders and response-rate statistics.

Everything runs **on your own computer with open-source models**: no paid API, no data sent to a chatbot.

> AAA (Advanced AI Algorithms) group project — Group 42: Charline Richard, Claire Shelby, Milo Carteyrade, Saoussen Zouari.

---

## 1. Quick start

**Requirements:** Python 3.10+ and ~2 GB of free disk space for the models. A GPU is not required.

```bash
# macOS / Linux
./run.sh
# Windows
run.bat
```

The first launch creates a virtual environment, installs the dependencies and starts the server. Then open **http://localhost:8000**.

Manual install, if you prefer:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # optional settings
python -m app.main
```

The first time you match offers and write a letter, the models download from Hugging Face (about 90 MB for the matcher and 3 GB for the writer). After that, everything works offline.

**Light mode (no AI download):** install only the "Core app" lines of `requirements.txt`. Landed then switches to TF-IDF matching and template letters. The coloured dot in the top bar tells you which engines are running (green = AI models, yellow = fallback).

## 2. User guide

### Step 1: Your CV
- Drop a **PDF, DOCX or TXT** CV in the box, or click **Try with Alex Martin's sample CV** (`data/sample_cv.pdf` is also there to test the upload).
- Landed shows the skills it found, grouped by category. Open **See how your CV was read** to check the sections.
- Tip: use a text-based PDF (exported from Word or Google Docs). A scanned image has no readable text.

### Step 2: Matching offers
- Type what you're looking for and where, then **Search**.
  - **Demo offers**: 22 synthetic internship offers shipped with the app (works offline).
  - **Live (Adzuna)**: real offers from the Adzuna API. Get free keys at https://developer.adzuna.com/signup and put them in `.env` (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`), then restart.
- **Paste an offer**: found something on JobTeaser, LinkedIn or Welcome to the Jungle? Paste its text. Landed scores it like the others. (We don't scrape these sites: their terms forbid it, and you choose what to bring.)
- Click an offer to see its **match score (0-100)** and its two components:
  - *Meaning of CV and offer*: semantic similarity between your CV and the offer.
  - *Required skills you have*: share of the skills mentioned in the offer that appear in your CV.
- **Write my cover letter and CV**: generates both. On a laptop without GPU it takes about 30-90 seconds.
  - *Cover letter* tab: editable text. A green banner confirms every skill mentioned is in your CV; a yellow one lists skills you never claimed.
  - *Tailored CV* tab: same facts as your CV, with the skills this offer asks for first and your bullet points re-ordered by relevance.
  - Download both as **.docx**, then **Add to board as applied**.

### Step 3: Application board
- Drag cards between columns (keyboard: focus a card and press **Alt + ←/→**).
- Click a card to add notes, a contact, the next step and its date.
- Applications sent 10+ days ago without news get a **Follow up** reminder.
- The header shows tracked / sent applications, response rate, interview rate and average match score.

Your data stays in `data/landed.db` (SQLite) and `data/cv.json` on your machine. Delete them to start fresh.

## 3. How it works (AI pipeline)

```
CV (PDF/DOCX) ──pypdf/python-docx──► text ──► sections + skills (rule-based extractor, 58 skills + aliases)
                                                │
offers (Adzuna API / pasted / demo) ────────────┤
                                                ▼
             score = 0.6 × semantic similarity  +  0.4 × skill coverage
             semantic: cosine similarity of all-MiniLM-L6-v2 sentence embeddings (fallback TF-IDF)
                                                │
                                                ▼
   Tailored CV: skills re-ordered + bullets ranked by embedding similarity to the offer (no rewriting of facts)
               + 2-sentence profile written by the LLM
   Cover letter: Qwen2.5-1.5B-Instruct (local, via transformers or Ollama), constrained prompt
                                                │
                                                ▼
   Guard: skills mentioned in generated text are checked against the CV; unsupported claims are flagged
```

Why it goes beyond a simple chatbot call:
- **Hybrid retrieval/ranking**: dense embeddings + explicit skill coverage, so a score is both accurate and explainable.
- **Retrieval-grounded generation**: the LLM only writes from the CV, the CV is restructured algorithmically, and an automatic **hallucination guard** checks the output.
- **Small open models, local inference**: free for every student, private by design, reproducible.
- **Graceful degradation**: the app always runs (TF-IDF + templates) even without models or internet.

Project layout:

```
app/main.py        FastAPI server and REST API
app/cv_parser.py   CV reading and section detection
app/skills.py      skill vocabulary and extraction
app/matcher.py     hybrid matching (embeddings / TF-IDF)
app/generator.py   tailored CV, cover letter (LLM), hallucination guard
app/sources.py     Adzuna API, pasted offers, demo dataset
app/crm.py         application board (SQLite)
app/export.py      .docx export
static/            front end (HTML/CSS/JS + Motion animations)
data/              demo offers, sample CV
```

## 4. Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | empty | Enables live offers |
| `LANDED_LLM` | `auto` | `auto`, `transformers`, `ollama` or `template` |
| `LANDED_HF_MODEL` | `Qwen/Qwen2.5-1.5B-Instruct` | Any Hugging Face chat model |
| `OLLAMA_MODEL` | `qwen2.5:1.5b` | Used if Ollama is running (faster on CPU) |
| `LANDED_EMBEDDINGS` | `auto` | `auto` (sentence-transformers) or `tfidf` |
| `PORT` | `8000` | Web server port |

**Faster on a laptop:** install [Ollama](https://ollama.com), run `ollama pull qwen2.5:1.5b`, keep it running. Landed detects it automatically.

## 5. Limits (honest list)

- The skill extractor knows 58 skills with aliases; skills outside this list are not counted in coverage (they still count in semantic similarity).
- A 1.5B-parameter model writes decent but simple letters: always re-read and edit. Bigger models (e.g. 7B via Ollama) write better and need more RAM.
- Adzuna has no "internship" filter: Landed adds internship keywords to the search, so some results may be other contracts. Adzuna returns a snippet of the description, not the full text.
- The demo offers are synthetic (fictional companies) and only for demonstration.

## 6. Credits and citations

See [CREDITS.md](CREDITS.md) for every package, model and dataset used, and [prompts_log.md](prompts_log.md) for the prompts we sent to AI assistants while building the project.
