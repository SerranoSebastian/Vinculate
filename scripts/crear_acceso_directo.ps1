$ErrorActionPreference = "Stop"

try {
    $ProjectDir = Split-Path -Parent $PSScriptRoot
    $Launcher = Join-Path $ProjectDir "INICIAR_SEDECO.bat"
    $Desktop = [Environment]::GetFolderPath("Desktop")
    $ShortcutPath = Join-Path $Desktop "Sistema Integral Vincúlate SEDECO.lnk"

    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $Launcher
    $Shortcut.WorkingDirectory = $ProjectDir
    $Shortcut.Description = "Abrir Sistema Integral Vincúlate SEDECO"
    $Shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,109"
    $Shortcut.Save()

    Write-Host "Acceso directo creado en el escritorio." -ForegroundColor Green
    exit 0
}
catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
