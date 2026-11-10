@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Construction de L-GPT.exe

echo ==========================================
echo       CONSTRUCTION DE L-GPT.EXE
echo ==========================================

if not exist ".venv\Scripts\python.exe" (
  echo [ERREUR] Environnement absent. Lance d'abord INSTALLER.bat.
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto error

python -m pip install --upgrade pyinstaller
if errorlevel 1 goto error

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist L-GPT.spec del /q L-GPT.spec

 echo.
echo Compilation en cours. Cela peut prendre plusieurs minutes...
echo Le journal complet sera enregistre dans build_exe.log.
echo.

REM PyInstaller possede deja des hooks Qt pour PySide6.
REM On evite --collect-all PySide6 qui inspecte aussi les scripts de deploiement
REM facultatifs et peut declencher un avertissement project_lib inutile.
python -m PyInstaller --noconfirm --clean --windowed --onedir ^
  --name "L-GPT" ^
  --icon "assets\lgpt.ico" ^
  --collect-all pymupdf ^
  --collect-all ollama ^
  --collect-all reportlab ^
  --hidden-import fitz ^
  --hidden-import numpy ^
  --hidden-import core.pdf_engine ^
  main.py > build_exe.log 2>&1

if errorlevel 1 goto build_error

if not exist "dist\L-GPT\L-GPT.exe" goto missing_exe

echo.
echo ==========================================
echo COMPILATION TERMINEE AVEC SUCCES
echo ==========================================
echo EXE : dist\L-GPT\L-GPT.exe
echo Conserve tout le dossier dist\L-GPT, pas seulement le fichier EXE.
echo Journal : build_exe.log
echo.
pause
exit /b 0

:build_error
echo.
echo [ERREUR] La compilation a echoue.
echo Les dernieres lignes du journal :
echo.
powershell -NoProfile -Command "Get-Content -Tail 45 'build_exe.log'"
echo.
echo Envoie-moi ces dernieres lignes pour identifier la vraie erreur.
pause
exit /b 1

:missing_exe
echo.
echo [ERREUR] PyInstaller s'est termine mais L-GPT.exe est introuvable.
echo Consulte build_exe.log.
powershell -NoProfile -Command "Get-Content -Tail 45 'build_exe.log'"
pause
exit /b 1

:error
echo.
echo [ERREUR] Impossible de preparer PyInstaller.
pause
exit /b 1
