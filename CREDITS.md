# Credits and citations

## Models (Hugging Face)
| Model | Use in Landed | License |
|---|---|---|
| [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | Sentence embeddings for CV ↔ offer matching and bullet ranking | Apache-2.0 |
| [Qwen/Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) | Local LLM writing the cover letter and CV profile | Apache-2.0 |

References:
- N. Reimers, I. Gurevych. *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*. EMNLP 2019. arXiv:1908.10084
- W. Wang et al. *MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers*. NeurIPS 2020. arXiv:2002.10957
- Qwen Team. *Qwen2 Technical Report*. 2024. arXiv:2407.10671

## Python packages
| Package | Use | License |
|---|---|---|
| [FastAPI](https://github.com/fastapi/fastapi) + [Uvicorn](https://github.com/encode/uvicorn) | Web server and REST API | MIT / BSD-3 |
| [sentence-transformers](https://github.com/UKPLab/sentence-transformers) | Embedding inference | Apache-2.0 |
| [transformers](https://github.com/huggingface/transformers), [PyTorch](https://github.com/pytorch/pytorch), [accelerate](https://github.com/huggingface/accelerate) | LLM inference | Apache-2.0 / BSD |
| [scikit-learn](https://github.com/scikit-learn/scikit-learn) | TF-IDF fallback matcher | BSD-3 |
| [pypdf](https://github.com/py-pdf/pypdf) | PDF text extraction | BSD-3 |
| [python-docx](https://github.com/python-openxml/python-docx) | DOCX reading and export | MIT |
| [requests](https://github.com/psf/requests), [NumPy](https://github.com/numpy/numpy) | HTTP calls, arrays | Apache-2.0 / BSD |

## Front end
- [Motion](https://motion.dev) (vanilla JS build, v14.6.0, bundled in `static/vendor/motion.js`) — animations. MIT (see `static/vendor/MOTION_LICENSE.md`).
- [Barlow and Barlow Condensed](https://github.com/jpt/barlow) by Jeremy Tribby, via [@fontsource](https://fontsource.org) — typefaces, bundled locally. SIL Open Font License 1.1.

## Bias check

### Research references
- D. Gaucher, J. Friesen, A. C. Kay. *Evidence That Gendered Wording in Job Advertisements Exists and Sustains Gender Inequality*. Journal of Personality and Social Psychology, 101(1), 109-128. American Psychological Association, 2011. DOI: 10.1037/a0022530
  — Source of the masculine/feminine word-stem lists in `app/bias_lexicon.py`.
- Reuters. *Amazon scraps secret AI recruiting tool that showed bias against women*. October 10, 2018.
  — Inspired the counterfactual fairness test: re-scoring the same CV with different candidate names to detect name-encoded signals in the embedding model.

### Legal references
- *Code du travail français, article L.1133-1* — prohibits hiring discrimination based on origin, sex, age, appearance, and other criteria unless the criterion is an essential and determining professional requirement. Basis for the LEGAL_RISK lexicon category.

## Data
- **Adzuna Jobs API** — live job offers, free developer tier. https://developer.adzuna.com
- **`data/demo_offers.json`** — 22 neutral synthetic internship offers + 3 intentionally biased ones (marked "contains bias") with fictional companies, written for this project with the help of Claude (Anthropic). Not real offers.
- **`data/sample_cv.txt` / `sample_cv.pdf`** — fictional CV ("Alex Martin"), written for this project.

## Optional
- [Ollama](https://ollama.com) — local model runner, MIT.

## AI assistants used during development
- **Claude (Anthropic)** — idea exploration, API research, code generation for the whole app, documentation. All prompts are in [prompts_log.md](prompts_log.md).
