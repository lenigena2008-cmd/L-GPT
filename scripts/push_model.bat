@echo off
REM Utilisation : push_model.bat C:\chemin\vers\modele.task
REM Envoie le modele sur le telephone par USB (beaucoup plus rapide que le selecteur de fichiers)
set ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe
if "%~1"=="" (echo Glisse un fichier .task sur ce script & pause & exit /b)
"%ADB%" shell mkdir -p /sdcard/Android/data/com.lgpt.mobile/files/models
"%ADB%" push "%~1" /sdcard/Android/data/com.lgpt.mobile/files/models/
echo Termine : ouvre L-GPT > Parametres > Moteur du telephone > Detecter les modeles
pause
