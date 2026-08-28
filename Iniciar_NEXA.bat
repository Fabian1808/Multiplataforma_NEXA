@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\pythonw.exe" goto :run

:missing
powershell -NoProfile -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('No se encontro el entorno virtual .venv.`nEjecute Instalar_NEXA.bat para configurarlo.', 'NEXA Productivity Hub', 'OK', 'Warning')" >nul 2>&1
exit /b 1

:run
start "" ".venv\Scripts\pythonw.exe" -m hub.app
exit /b 0