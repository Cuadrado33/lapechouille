@echo off
set SRC=%~dp0surfcasting.db
set DST=%USERPROFILE%\Desktop\surfcasting_backup_%date:~6,4%-%date:~3,2%-%date:~0,2%.db
if exist "%SRC%" (
    copy "%SRC%" "%DST%"
    echo ✅ Base sauvegardée sur le Bureau : surfcasting_backup_%date:~6,4%-%date:~3,2%-%date:~0,2%.db
) else (
    echo ❌ Fichier surfcasting.db introuvable
)
pause
