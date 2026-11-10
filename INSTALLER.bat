@echo off
setlocal
cd /d "%~dp0"
title Installation de L-GPT
echo ==========================================
echo              INSTALLATION L-GPT
echo ==========================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python est introuvable. Installe Python 3.11 ou plus recent et coche Add Python to PATH.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto error
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto error
python -m pip install -r requirements.txt
if errorlevel 1 goto error
echo.
echo Installation terminee avec succes.
echo Tu peux maintenant lancer L-GPT.bat.
echo Ollama doit etre installe, demarre et contenir les modeles necessaires.
echo.
pause
exit /b 0
:error
echo.
echo [ERREUR] Installation interrompue. Lis les messages ci-dessus.
pause
exit /b 1
