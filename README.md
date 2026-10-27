# Landed ✈ — from CV to internship, on one board

**Landed** is an open-source AI assistant for the internship hunt. You drop your CV, and it:

1. **Reads your CV** and extracts your skills, experiences and projects.
2. **Ranks internship offers** by how well they fit you, and explains why (skills you have, skills the offer also asks for).
3. **Writes a tailored cover letter and CV version** for each offer, using only facts from your CV, and **flags any skill you never claimed**.
4. **Tracks every application** on a departures-style board (saved → applied → interview → offer / rejected), with follow-up reminders and response-rate statistics.
5. **Checks every offer for bias** — wording that may be discriminatory under French law, exclusionary language, gender-coded vocabulary, and a counterfactual fairness test on our own matching model (inspired by the Amazon recruiting AI incident).

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

Full install options (manual setup, light mode without AI downloads, `.env` configuration reference): see **[INSTALL.md](INSTALL.md)**.

## 2. User guide

Your CV in, matched offers out, a tailored cover letter and CV, a bias check on every offer, and an application board to track it all — see **[USER_GUIDE.md](USER_GUIDE.md)** for the full walkthrough.

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
                                                │
                                                ▼
   Bias check (offer wording):
     ├─ LEGAL_RISK: regex against Code du travail L.1132-1 patterns (age, appearance) — EN + FR
     ├─ EXCLUSIONARY: native speaker / mother tongue / langue maternelle
     └─ GENDER_CODED: word-stem matching (Gaucher et al. 2011) — counts masculine vs feminine signals

   Counterfactual fairness test (our own model):
     └─ Re-score the CV with 3 name variants (male / female / neutral) — flag if delta > 3 pts
```

Why it goes beyond a simple chatbot call:
- **Hybrid retrieval/ranking**: dense embeddings + explicit skill coverage, so a score is both accurate and explainable.
- **Retrieval-grounded generation**: the LLM only writes from the CV, the CV is restructured algorithmically, and an automatic **hallucination guard** checks the output.
- **Small open models, local inference**: free for every student, private by design, reproducible.
- **Graceful degradation**: the app always runs (TF-IDF + templates) even without models or internet.
- **Responsible AI by design**: bias checks run on every offer (wording) and on our own model (counterfactual test), making the system's limitations visible rather than hidden.

Project layout:

```
app/main.py          FastAPI server and REST API
app/cv_parser.py     CV reading and section detection
app/skills.py        skill vocabulary and extraction
app/matcher.py       hybrid matching (embeddings / TF-IDF)
app/generator.py     tailored CV, cover letter (LLM), hallucination guard
app/sources.py       Adzuna API, pasted offers, demo dataset
app/crm.py           application board (SQLite)
app/export.py        .docx export
app/bias.py          wording analysis + counterfactual fairness test
app/bias_lexicon.py  rule-based lexicon (legal risk, exclusionary, gender-coded)
static/              front end (HTML/CSS/JS + Motion animations)
data/                demo offers (23 neutral + 2 biased), sample CV
```

## 4. Limits (honest list)

- The skill extractor knows 58 skills with aliases; skills outside this list are not counted in coverage (they still count in semantic similarity).
- A 1.5B-parameter model writes decent but simple letters: always re-read and edit. Bigger models (e.g. 7B via Ollama) write better and need more RAM.
- Adzuna has no "internship" filter: Landed adds internship keywords to the search, so some results may be other contracts. Adzuna returns a snippet of the description, not the full text.
- The demo offers are synthetic (fictional companies). 2 of the 25 are intentionally biased so the bias checker has something to find.
- The bias checker is rule-based and incomplete — it does not catch every form of bias, only the patterns in the lexicon. A delta ≤ 3 in the counterfactual test does not prove the model is fair, only that it is not sensitive to the name signals we tested.

## 5. Credits and citations

See [CREDITS.md](CREDITS.md) for every package, model and dataset used, and [prompts_log.md](prompts_log.md) for the prompts we sent to AI assistants while building the project.
