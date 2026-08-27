@echo off
setlocal
title Limpieza de NEXA Productivity Hub
cd /d "%~dp0"

echo ============================================
echo  Limpieza de procesos NEXA colgados
echo ============================================
echo.
echo Se cerraran todos los procesos de NEXA que
echo puedan estar reteniendo el acceso a la app.
echo.
set /p CONFIRM="Continuar? (S/N): "
if /i not "%CONFIRM%"=="S" (
    echo Cancelado.
    pause
    exit /b 0
)

echo.
echo Buscando procesos NEXA...
taskkill /f /im nexa-hub.exe >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE eq NEXA*" >nul 2>&1

wmic process where "name='python.exe' and commandline like '%%hub.app%%'" call terminate >nul 2>&1
wmic process where "name='python.exe' and commandline like '%%nexa-hub%%'" call terminate >nul 2>&1
wmic process where "name='python3.13.exe' and commandline like '%%hub.app%%'" call terminate >nul 2>&1
wmic process where "name='python3.13.exe' and commandline like '%%nexa-hub%%'" call terminate >nul 2>&1

echo.
echo Procesos NEXA terminados. Ahora puede abrir la app
echo con doble clic en:  Iniciar_NEXA.bat
echo.
pause
endlocal

