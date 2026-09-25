$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Dir = Join-Path $Root ".streamlit"
$File = Join-Path $Dir "secrets.toml"
New-Item -ItemType Directory -Force -Path $Dir | Out-Null
Write-Host "=== CONFIGURAR VINCULATE EN SUPABASE ===" -ForegroundColor Cyan
$url = Read-Host "Pega Project URL (https://....supabase.co)"
$key = Read-Host "Pega la anon/public key"
if ([string]::IsNullOrWhiteSpace($url) -or [string]::IsNullOrWhiteSpace($key)) {
  Write-Host "URL o key vacia. No se modifico nada." -ForegroundColor Red
  exit 1
}
$content = @"
[supabase]
url = "$url"
key = "$key"
"@
Set-Content -Path $File -Value $content -Encoding UTF8
Write-Host "Configuracion guardada en $File" -ForegroundColor Green
Write-Host "Ahora inicia/reinicia el Sistema Vinculate." -ForegroundColor Green
Read-Host "Presiona Enter para cerrar"
