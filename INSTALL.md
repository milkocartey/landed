# Landed — Installation Guide

This guide takes you from a computer with nothing installed to Landed running in your browser. It covers **macOS**, **Windows** and **Linux**. Expect about **15–30 minutes** the first time, mostly downloads.

Once it runs, see `USER_GUIDE.md` for how to use the app.

---

## Contents
1. [What you need](#1-what-you-need)
2. [Install Python](#2-install-python)
3. [Get the project](#3-get-the-project)
4. [Run Landed (one command)](#4-run-landed-one-command)
5. [First use: model downloads](#5-first-use-model-downloads)
6. [Stop, restart, update](#6-stop-restart-update)
7. [Manual installation (if the script fails)](#7-manual-installation-if-the-script-fails)
8. [Optional settings](#8-optional-settings)
9. [Troubleshooting](#9-troubleshooting)
10. [Uninstall](#10-uninstall)

---

## 1. What you need

| | Minimum |
|---|---|
| System | macOS, Windows 10/11, or Linux |
| Python | **3.10 or newer** (tested on 3.11; 3.10/3.12 expected to work the same, no version-specific code) |
| Disk space | about **5 GB free** (measured: ~1.2 GB for the Python virtual environment + dependencies, ~3 GB for the Hugging Face model cache) |
| RAM | 8 GB recommended for the AI writer; less works in light mode |
| Internet | needed for the first launch only |
| GPU | **not required** |

---

## 2. Install Python

First check whether you already have it. Open a terminal:
- **macOS:** `Cmd + Space`, type **Terminal**, press Enter.
- **Windows:** Start menu, type **PowerShell**, press Enter.
- **Linux:** your usual terminal.

Then run:

| macOS / Linux | Windows |
|---|---|
| `python3 --version` | `python --version` |

If it prints `Python 3.10` or higher, skip to step 3. Otherwise:

### macOS
1. Download the latest **macOS installer** from https://www.python.org/downloads/ and run it.
2. Close and reopen Terminal, then check again with `python3 --version`.

> If macOS asks to install "command line developer tools", accept: it is Apple's standard developer package.

### Windows
1. Download the latest **Windows installer (64-bit)** from https://www.python.org/downloads/.
2. In the first screen of the installer, **tick "Add python.exe to PATH"**, then click **Install Now**.
3. Close and reopen PowerShell, then check again with `python --version`.

> If `python` opens the Microsoft Store instead, Windows is using a shortcut. Go to **Settings → Apps → Advanced app settings → App execution aliases** and turn off the two "python" aliases, then reopen PowerShell.

### Linux (Debian / Ubuntu)
```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```
The `python3-venv` package is needed to create the virtual environment.

---

## 3. Get the project

The code is on GitHub: **https://github.com/milkocartey/landed**

The repository is public: no GitHub account needed.

**Option A — Download ZIP (easiest, no Git needed)**
1. Open the repository link above.
2. Click the green **Code** button, then **Download ZIP**.
3. Unzip it. GitHub names the folder `landed-main`: rename it `landed` and move it somewhere easy, for example your Downloads folder.

**Option B — Git (if you already use it; easier to update later)**
```bash
cd ~/Downloads
git clone https://github.com/milkocartey/landed landed
```
(Windows: `cd $HOME\Downloads` first.)

Then go into the folder in the terminal:

| macOS / Linux | Windows (PowerShell) |
|---|---|
| `cd ~/Downloads/landed` | `cd $HOME\Downloads\landed` |

Adapt the path if your folder is elsewhere. Tip: type `cd ` (with a space) and drag the folder into the terminal window, then press Enter.

Check you are in the right place: the folder must contain `run.sh`, `run.bat`, `requirements.txt` and an `app` folder.

| macOS / Linux | Windows |
|---|---|
| `ls` | `dir` |

---

## 4. Run Landed (one command)

### macOS / Linux
```bash
chmod +x run.sh
./run.sh
```
(`chmod` is only needed the first time.)

### Windows
```powershell
.\run.bat
```
You can also double-click `run.bat` in the file explorer.

### What happens
The first launch:
1. creates a private Python environment in a `.venv` folder (nothing is installed system-wide),
2. installs the dependencies from `requirements.txt` (several minutes),
3. creates your settings file `.env` from `.env.example`,
4. starts the server.

Leave this terminal open: it **is** the app. When it says the server is running, open your browser at:

### **http://localhost:8000**

Or from a second terminal:

| macOS | Windows | Linux |
|---|---|---|
| `open http://localhost:8000` | `start http://localhost:8000` | `xdg-open http://localhost:8000` |

### Check it works
- The page loads with the Landed interface.
- The **dot in the top bar** shows the engines: **green** = AI models, **yellow** = fallback mode (simpler matching and template letters).
- Click the **sample CV** button: skills should appear.

---

## 5. First use: model downloads

The first time you match an offer and generate a letter, Landed downloads two open-source models from Hugging Face:

| Model | Role | Size |
|---|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | matching CV ↔ offer | ~90 MB |
| `Qwen/Qwen2.5-1.5B-Instruct` | writing letters and CVs | ~3 GB |

- This happens **once**. Do it on good wifi, and **not just before filming the demo**.
- Progress is shown in the terminal, not in the browser. The first generation can look stuck: check the terminal.
- Models are stored in the Hugging Face cache:
  - macOS / Linux: `~/.cache/huggingface/hub`
  - Windows: `C:\Users\<you>\.cache\huggingface\hub`

After that, Landed works offline.

---

## 6. Stop, restart, update

| Action | How |
|---|---|
| **Stop** | In the terminal running the app, press `Ctrl + C` |
| **Restart** | `cd` into the folder, then `./run.sh` (macOS/Linux) or `.\run.bat` (Windows). Much faster after the first time. |
| **Reset your data** (CV + board) | Stop the app, delete `data/cv.json` and `data/landed.db`, restart |
| **Update the code** | Git: `git pull`. Zip: download the new zip and copy your `.env` into it. If `requirements.txt` changed, delete the `.venv` folder and run the script again. |

---

## 7. Manual installation (if the script fails)

Run these from the project folder, one line at a time.

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

### Windows (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python -m app.main
```

> If PowerShell refuses `activate` with a message about "running scripts is disabled", run this once, then retry:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
> Or skip activation and call the environment directly: `.venv\Scripts\python -m app.main`

Next time, you only need:
```bash
source .venv/bin/activate     # Windows: .venv\Scripts\activate
python -m app.main
```

---

## 8. Optional settings

Settings live in the `.env` file in the project folder (open it with any text editor). **Restart the app** after any change.

| Setting | Default | What it does |
|---|---|---|
| `LANDED_EMBEDDINGS` | `auto` | `tfidf` = light matching, no model download |
| `LANDED_EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Matching model |
| `LANDED_LLM` | `auto` | `transformers`, `ollama`, or `template` (no AI writer) |
| `LANDED_HF_MODEL` | `Qwen/Qwen2.5-1.5B-Instruct` | Writing model |
| `OLLAMA_MODEL`, `OLLAMA_URL` | `qwen2.5:1.5b`, `http://localhost:11434` | Only if you use Ollama |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | empty | Free keys from https://developer.adzuna.com for the "Adzuna" live offer source |
| `FT_CLIENT_ID`, `FT_CLIENT_SECRET` | empty | Free keys from https://francetravail.io/data/api for the "France Travail" live offer source |
| `PORT` | `8000` | Change if port 8000 is busy, then open `http://localhost:<new port>` |

Note: `.env.example` does not list `FT_CLIENT_ID`/`FT_CLIENT_SECRET` yet (only the Adzuna keys) — add the two lines yourself if you want to use the France Travail live source.

The **Demo offers**, **Vraies offres (France 2026)**, **France Travail** and **Adzuna** buttons on the Offers screen are always visible; the two live sources (France Travail, Adzuna) are greyed out until their keys are set.

### Light mode (old or small computer, slow internet)
In `.env`:
```
LANDED_EMBEDDINGS=tfidf
LANDED_LLM=template
```
No model download. Matching and letters are simpler, and the dot turns yellow. Everything else works.

### Using Ollama instead (optional)
If you already use Ollama (https://ollama.com):
```bash
ollama pull qwen2.5:1.5b
```
Keep Ollama running, and leave `LANDED_LLM=auto`: Landed uses Ollama when it is available.

---

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| `python: command not found` / `python3: command not found` | Python is not installed or not in PATH. See step 2. On Windows, reinstall and tick "Add python.exe to PATH". |
| `python` opens the Microsoft Store (Windows) | Turn off the python "App execution aliases" (see step 2). |
| `./run.sh: Permission denied` | Run `chmod +x run.sh` once. |
| `No such file or directory: run.sh` | You are not in the project folder. Use `cd` (step 3) and check with `ls` / `dir`. |
| `ensurepip is not available` / venv error (Linux) | `sudo apt install python3-venv`, delete `.venv`, retry. |
| `pip install` fails halfway | Check your internet and free disk space, delete the `.venv` folder, run the script again. Copy the **last lines** of the error to the group. |
| `Address already in use` / port 8000 busy | Another app uses the port. Set `PORT=8001` in `.env`, restart, open http://localhost:8001. Or find it: `lsof -i :8000` (macOS/Linux), `netstat -ano \| findstr :8000` (Windows). |
| Browser says "can't connect" | The terminal with the app was closed or crashed. Look at it, restart with the script. |
| Yellow dot in the top bar | The AI models didn't load: no internet at first launch, not enough disk or RAM. Read the terminal message. The app still works in fallback mode. |
| First letter takes forever | The 3 GB model is downloading: watch the terminal. Later generations are faster, but still slower on CPU than a cloud chatbot. |
| `Killed` or the app crashes during generation | Not enough RAM. Close other apps, or use light mode (step 8). |
| No skills detected in my CV | Your PDF is a scanned image. Export a text PDF from Word / Google Docs, or paste the text. |

When asking the group for help, send: your system (Mac/Windows/Linux), your Python version, and the last ~10 lines of the terminal.

---

## 10. Uninstall

1. Stop the app (`Ctrl + C`).
2. Delete the project folder (this also removes `.venv`, your CV and your board).
3. To free the model space, delete the two model folders in the Hugging Face cache (see step 5), named `models--sentence-transformers--all-MiniLM-L6-v2` and `models--Qwen--Qwen2.5-1.5B-Instruct`.

Python itself can stay: other programs may use it.
