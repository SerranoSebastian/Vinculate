@echo off
chcp 65001 >nul
setlocal
title Sistema Integral Vincúlate SEDECO - Reparación
cd /d "%~dp0"

echo.
echo ==> Reparando el entorno local de SEDECO
if exist ".sedeco_runtime\venv" rmdir /s /q ".sedeco_runtime\venv"
if exist ".sedeco_runtime\requirements.sha256" del /f /q ".sedeco_runtime\requirements.sha256"
if exist ".sedeco_runtime\launcher.version" del /f /q ".sedeco_runtime\launcher.version"
if exist ".sedeco_runtime\server.pid" del /f /q ".sedeco_runtime\server.pid"
if exist ".sedeco_runtime\server.port" del /f /q ".sedeco_runtime\server.port"

echo.
echo Reparación preparada. Ahora se iniciará SEDECO y se reinstalarán los componentes.
call "%~dp0INICIAR_SEDECO.bat"
exit /b %ERRORLEVEL%
