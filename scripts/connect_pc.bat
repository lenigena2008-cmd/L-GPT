@echo off
REM Connexion USB téléphone <-> PC pour L-GPT (moteur "PC" via Ollama)
set ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe
echo --- Appareils connectes ---
"%ADB%" devices
echo --- Redirection du port Ollama via le cable USB ---
"%ADB%" reverse tcp:11434 tcp:11434
tasklist | find /i "ollama" >nul || start "" ollama serve
echo.
echo OK : dans L-GPT, utilise l'adresse http://127.0.0.1:11434
pause
