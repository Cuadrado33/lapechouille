# ================================================================
# La Péchouille — Installer la tâche de backup automatique
# Lance ce script UNE FOIS en tant qu'administrateur
# ================================================================

$AppDir  = "C:\Users\jerome\OneDrive\CODAGE\00_En cours\Surfcasting_J2"
$Script  = "$AppDir\backup_supabase.py"
$LogFile = "$AppDir\backups_supabase\backup.log"

# Trouver py.exe
$PyExe = (Get-Command py -ErrorAction SilentlyContinue)?.Source
if (-not $PyExe) {
    $PyExe = "C:\Windows\py.exe"
}

Write-Host "✅ Python : $PyExe"
Write-Host "✅ Script : $Script"

# Créer l'action
$Action  = New-ScheduledTaskAction `
    -Execute $PyExe `
    -Argument "`"$Script`"" `
    -WorkingDirectory $AppDir

# Toutes les 2 heures
$Trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Hours 2) -Once -At (Get-Date)

# Paramètres
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -RunOnlyIfNetworkAvailable `
    -StartWhenAvailable

# Enregistrer
Register-ScheduledTask `
    -TaskName   "LaPechouille_Backup" `
    -TaskPath   "\LaPechouille\" `
    -Action     $Action `
    -Trigger    $Trigger `
    -Settings   $Settings `
    -RunLevel   Highest `
    -Force

Write-Host ""
Write-Host "🎉 Tâche planifiée installée !"
Write-Host "   Backup automatique toutes les 2 heures"
Write-Host "   Les fichiers JSON sont dans : $AppDir\backups_supabase\"
Write-Host ""
Write-Host "Pour lancer un backup immédiat :"
Write-Host "   py backup_supabase.py"
