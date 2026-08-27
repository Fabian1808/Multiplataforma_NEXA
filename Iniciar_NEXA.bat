@echo off
setlocal
title NEXA Productivity Hub
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto :run
echo [ERROR] No se encontro el entorno virtual .venv
echo Ejecute primero:  python -m venv .venv
echo Luego:            .venv\Scripts\python.exe -m pip install -e .
pause
exit /b 1

:run
echo Iniciando NEXA Productivity Hub...
".venv\Scripts\python.exe" -m hub.app
if errorlevel 1 goto :err
exit /b 0

:err
echo.
echo La aplicacion termino con un error.
echo Revise los logs en:  %APPDATA%\NEXA\ProductivityHub\logs
pause
exit /b 1

