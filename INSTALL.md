# Install

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

## Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | empty | Enables live offers |
| `FT_CLIENT_ID`, `FT_CLIENT_SECRET` | empty | Enables live France Travail offers — free keys at https://francetravail.io/data/api |
| `LANDED_LLM` | `auto` | `auto`, `transformers`, `ollama` or `template` |
| `LANDED_HF_MODEL` | `Qwen/Qwen2.5-1.5B-Instruct` | Any Hugging Face chat model |
| `OLLAMA_MODEL` | `qwen2.5:1.5b` | Used if Ollama is running (faster on CPU) |
| `LANDED_EMBEDDINGS` | `auto` | `auto` (sentence-transformers) or `tfidf` |
| `PORT` | `8000` | Web server port |

**Faster on a laptop:** install [Ollama](https://ollama.com), run `ollama pull qwen2.5:1.5b`, keep it running. Landed detects it automatically.

See the main [README](README.md) for what the app does, and [USER_GUIDE.md](USER_GUIDE.md) for how to use it once it's running.
