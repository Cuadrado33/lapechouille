@echo off
REM Lancer l'app Surfcasting avec backup automatique de la base de données

set APP_DIR=%~dp0
set DB_FILE=%APP_DIR%surfcasting.db
set BACKUP_DIR=%APP_DIR%backups

REM Créer le dossier backups si nécessaire
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Copier la DB avec horodatage (si elle existe et a des données)
if exist "%DB_FILE%" (
    for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set dt=%%I
    set BACKUP_NAME=surfcasting_backup_%dt:~0,8%_%dt:~8,6%.db
    copy "%DB_FILE%" "%BACKUP_DIR%\%BACKUP_NAME%" >nul 2>&1
    echo [OK] Backup cree : %BACKUP_NAME%
) else (
    echo [INFO] Pas de base de donnees existante
)

REM Garder seulement les 10 derniers backups
for /f "skip=10 delims=" %%F in ('dir /b /o-d "%BACKUP_DIR%\surfcasting_backup_*.db" 2^>nul') do del "%BACKUP_DIR%\%%F" >nul 2>&1

REM Lancer l'app
echo [INFO] Demarrage de l'application...
cd "%APP_DIR%"
python -m streamlit run app.py
