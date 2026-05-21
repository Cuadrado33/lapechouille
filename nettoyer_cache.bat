@echo off
cd /d "%~dp0"
echo Nettoyage des caches Python...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s/q "%%d"
echo OK - Caches supprimés. Tu peux relancer l'appli.
pause
