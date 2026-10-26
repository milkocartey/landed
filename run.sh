#!/usr/bin/env bash
# Landed - one-command launcher (macOS / Linux)
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Creating virtual environment and installing dependencies (first run only, a few minutes)..."
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
fi
[ -f .env ] || cp .env.example .env
./.venv/bin/python -m app.main
