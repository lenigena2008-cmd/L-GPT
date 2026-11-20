#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
  echo "L'environnement Python est absent. Lance d'abord ./INSTALLER.sh"
  read -r -p "Appuie sur Entrée pour fermer..."
  exit 1
fi
if [ ! -f "main.py" ]; then
  echo "main.py est introuvable. Vérifie que l'archive est entièrement extraite."
  read -r -p "Appuie sur Entrée pour fermer..."
  exit 1
fi
exec .venv/bin/python main.py
