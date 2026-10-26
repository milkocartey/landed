@echo off
REM Landed - one-command launcher (Windows)
cd /d "%~dp0"
if not exist .venv (
  echo Creating virtual environment and installing dependencies (first run only, a few minutes)...
  python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\pip install -r requirements.txt
)
if not exist .env copy .env.example .env
.venv\Scripts\python -m app.main
pause
