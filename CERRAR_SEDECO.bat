@echo off
chcp 65001 >nul
setlocal
title Sistema Integral Vincúlate SEDECO - Cerrar
cd /d "%~dp0"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\cerrar_sedeco.ps1"
set "SEDECO_EXIT=%ERRORLEVEL%"

if not "%SEDECO_EXIT%"=="0" pause
exit /b %SEDECO_EXIT%
