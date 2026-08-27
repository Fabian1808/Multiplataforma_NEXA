@echo off
setlocal
title Instalacion de NEXA Productivity Hub
cd /d "%~dp0"

echo ============================================
echo  Instalacion de NEXA Productivity Hub
echo ============================================
echo.

rem 1) Verificar que Python esta disponible
python --version >nul 2>&1
if errorlevel 1 goto :no_python
echo [1/3] Python detectado.

rem 2) Crear entorno virtual si no existe
if exist ".venv\Scripts\python.exe" goto :venv_ok
echo [2/3] Creando entorno virtual .venv ...
python -m venv .venv
if errorlevel 1 goto :no_venv
goto :venv_done

:venv_ok
echo [2/3] Entorno virtual ya existe, se omitira su creacion.

:venv_done
rem 3) Instalar el proyecto y sus dependencias
echo [3/3] Instalando dependencias (puede tardar unos minutos)...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto :dep_fail

echo.
echo ============================================
echo  Instalacion completada correctamente.
echo  Para abrir el Hub, ejecute:  Iniciar_NEXA.bat
echo ============================================
echo.
pause
exit /b 0

:no_python
echo [ERROR] Python no esta instalado o no esta en el PATH.
echo Instale Python 3.11 o superior desde python.org/downloads
pause
exit /b 1

:no_venv
echo [ERROR] No se pudo crear el entorno virtual.
pause
exit /b 1

:dep_fail
echo [ERROR] Fallo la instalacion de dependencias.
pause
exit /b 1

