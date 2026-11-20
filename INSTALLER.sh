#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

printf '\n==========================================\n'
printf '          INSTALLATION DE L-GPT\n'
printf '==========================================\n\n'

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 est introuvable. Installe Python 3.11 ou plus récent."
  exit 1
fi
PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
  echo "Python 3.11 ou plus récent est requis (détecté : ${PYTHON_VERSION})."
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo ""
echo "Installation terminée. Lance ./L-GPT.command"
echo "Ollama doit être installé et démarré séparément."
