#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
  echo "Lance d'abord ./INSTALLER.sh"
  exit 1
fi
.venv/bin/python -m pip install --upgrade pyinstaller
rm -rf build dist
.venv/bin/python -m PyInstaller --noconfirm --clean --windowed --onedir \
  --name "L-GPT" \
  --add-data "assets:assets" \
  --collect-all pymupdf \
  --collect-all ollama \
  --collect-all reportlab \
  --hidden-import fitz \
  --hidden-import numpy \
  --hidden-import core.pdf_engine \
  main.py
printf '\nApplication créée dans dist/L-GPT.app (si le bundle PyInstaller est généré sur cette version).\n'
printf 'Ollama reste à installer séparément sur le Mac cible.\n'
