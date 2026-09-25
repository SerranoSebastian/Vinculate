@echo off
chcp 65001 >nul
setlocal
title Sistema Integral Vincúlate SEDECO - Acceso directo
cd /d "%~dp0"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\crear_acceso_directo.ps1"
set "SEDECO_EXIT=%ERRORLEVEL%"

echo.
pause
exit /b %SEDECO_EXIT%
