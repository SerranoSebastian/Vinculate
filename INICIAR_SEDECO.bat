@echo off
chcp 65001 >nul
setlocal
title Sistema Integral Vincúlate SEDECO - Inicio
cd /d "%~dp0"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar_sedeco.ps1"
set "SEDECO_EXIT=%ERRORLEVEL%"

if not "%SEDECO_EXIT%"=="0" (
    echo.
    echo No fue posible iniciar el Sistema Integral Vincúlate SEDECO.
    echo Revisa el mensaje anterior y vuelve a intentarlo.
    echo.
    pause
)

exit /b %SEDECO_EXIT%
