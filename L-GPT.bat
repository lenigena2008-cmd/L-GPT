@echo off
setlocal
cd /d "%~dp0"
title L-GPT 2.9 - Demarrage
if not exist ".venv\Scripts\pythonw.exe" (
  echo [ERREUR] L'environnement Python de L-GPT est absent.
  echo Lance INSTALLER.bat et attends le message de fin.
  echo.
  pause
  exit /b 1
)
if not exist "main.py" (
  echo [ERREUR] main.py est introuvable. Le ZIP doit etre entierement extrait.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import PySide6, pymupdf, numpy, ollama, reportlab" >nul 2>&1
if errorlevel 1 (
  echo [ERREUR] Une dependance manque. Relance INSTALLER.bat.
  pause
  exit /b 1
)
start "L-GPT" ".venv\Scripts\pythonw.exe" "%~dp0main.py"
if errorlevel 1 (
  echo [ERREUR] Impossible de lancer L-GPT. Consulte L-GPT_erreurs.log.
  pause
  exit /b 1
)
exit /b 0
