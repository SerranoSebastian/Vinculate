$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $ProjectDir ".sedeco_runtime"
$VenvPython = Join-Path $RuntimeDir "venv\Scripts\python.exe"
$PidFile = Join-Path $RuntimeDir "server.pid"
$PortFile = Join-Path $RuntimeDir "server.port"

try {
    if (-not (Test-Path $PidFile)) {
        Write-Host "El Sistema Integral Vincúlate SEDECO no esta ejecutandose." -ForegroundColor Yellow
        exit 0
    }

    $ServerPid = [int](Get-Content $PidFile -Raw)
    $Process = Get-Process -Id $ServerPid -ErrorAction SilentlyContinue
    if ($Process) {
        if ($Process.Path -ne $VenvPython) {
            Remove-Item $PidFile, $PortFile -Force -ErrorAction SilentlyContinue
            throw "El identificador guardado ya no pertenece al servidor SEDECO; no se cerro ningun otro proceso."
        }
        Stop-Process -Id $ServerPid -Force
        Write-Host "Sistema Integral Vincúlate SEDECO cerrado correctamente." -ForegroundColor Green
    }
    else {
        Write-Host "La instancia ya estaba cerrada." -ForegroundColor Yellow
    }

    Remove-Item $PidFile, $PortFile -Force -ErrorAction SilentlyContinue
    exit 0
}
catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
