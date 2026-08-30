@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

rem ============================================================
rem  NEXA Productivity Hub — Lanzador Unificado
rem  Doble-clic aqui para instalar y/o iniciar la plataforma.
rem ============================================================

rem --- Verificacion rapida: si el venv ya esta listo, arrancar directo ---
if exist ".venv\Scripts\pythonw.exe" goto :launch

rem --- Primer uso o venv borrado: instalar automaticamente ---
echo NEXA Productivity Hub — Configuracion inicial...
echo.

rem --- Comprobar que Python este disponible en el sistema ---
python --version >nul 2>&1
if errorlevel 1 (
    powershell -NoProfile -Command ^
      "Add-Type -AssemblyName PresentationFramework; ^
       [System.Windows.MessageBox]::Show( ^
         'Python no esta instalado o no esta en el PATH.`n`nDescargalo desde python.org/downloads`n(version 3.11 o superior) y asegurate de marcar la opcion:`n[x] Add Python to PATH', ^
         'NEXA — Requisito faltante', ^
         'OK', 'Warning')"
    exit /b 1
)

rem --- Mostrar ventana de progreso mientras instalamos ---
rem     (la ventana se cierra automaticamente al terminar)
powershell -NoProfile -WindowStyle Hidden -Command ^
  "Add-Type -AssemblyName System.Windows.Forms; ^
   Add-Type -AssemblyName System.Drawing; ^
   $f = New-Object System.Windows.Forms.Form; ^
   $f.Text = 'NEXA Productivity Hub'; ^
   $f.Size = New-Object System.Drawing.Size(460, 200); ^
   $f.StartPosition = 'CenterScreen'; ^
   $f.FormBorderStyle = 'FixedDialog'; ^
   $f.MaximizeBox = $false; ^
   $f.MinimizeBox = $false; ^
   $f.BackColor = [System.Drawing.Color]::FromArgb(30, 30, 46); ^
   $title = New-Object System.Windows.Forms.Label; ^
   $title.Text = 'NEXA'; ^
   $title.Font = New-Object System.Drawing.Font('Segoe UI', 22, [System.Drawing.FontStyle]::Bold); ^
   $title.ForeColor = [System.Drawing.Color]::FromArgb(255, 85, 3); ^
   $title.AutoSize = $true; ^
   $title.Location = New-Object System.Drawing.Point(175, 20); ^
   $sub = New-Object System.Windows.Forms.Label; ^
   $sub.Text = 'Configurando la plataforma...'; ^
   $sub.Font = New-Object System.Drawing.Font('Segoe UI', 10); ^
   $sub.ForeColor = [System.Drawing.Color]::FromArgb(160, 160, 184); ^
   $sub.AutoSize = $true; ^
   $sub.Location = New-Object System.Drawing.Point(130, 60); ^
   $bar = New-Object System.Windows.Forms.ProgressBar; ^
   $bar.Style = 'Marquee'; ^
   $bar.MarqueeAnimationSpeed = 30; ^
   $bar.Location = New-Object System.Drawing.Point(30, 100); ^
   $bar.Size = New-Object System.Drawing.Size(400, 16); ^
   $bar.ForeColor = [System.Drawing.Color]::FromArgb(255, 85, 3); ^
   $status = New-Object System.Windows.Forms.Label; ^
   $status.Text = 'Instalando dependencias de Python...'; ^
   $status.Font = New-Object System.Drawing.Font('Segoe UI', 9); ^
   $status.ForeColor = [System.Drawing.Color]::FromArgb(110, 110, 136); ^
   $status.AutoSize = $true; ^
   $status.Location = New-Object System.Drawing.Point(100, 125); ^
   $f.Controls.AddRange(@($title, $sub, $bar, $status)); ^
   $f.Show(); ^
   $f.Update(); ^
   [System.IO.File]::WriteAllText('%~dp0.nexa_install_ui_ready', '1'); ^
   while (-not [System.IO.File]::Exists('%~dp0.nexa_install_done')) { ^
     [System.Windows.Forms.Application]::DoEvents(); ^
     Start-Sleep -Milliseconds 100; ^
   } ^
   [System.IO.File]::Delete('%~dp0.nexa_install_done'); ^
   if ([System.IO.File]::Exists('%~dp0.nexa_install_failed')) { ^
     [System.IO.File]::Delete('%~dp0.nexa_install_failed'); ^
     [System.Windows.MessageBox]::Show('Ocurrio un error al instalar las dependencias.`nVerifica tu conexion a internet e intenta de nuevo.', 'NEXA — Error de instalacion', 'OK', 'Error'); ^
   } ^
   $f.Close()" &

rem --- Esperar a que la ventana de UI este lista ---
:wait_ui
if not exist ".nexa_install_ui_ready" (
    timeout /t 1 /nobreak >nul
    goto :wait_ui
)
del ".nexa_install_ui_ready" >nul 2>&1

rem --- Crear entorno virtual ---
echo Creando entorno virtual .venv...
python -m venv .venv >nul 2>&1
if errorlevel 1 (
    echo 1 > ".nexa_install_failed"
    echo 1 > ".nexa_install_done"
    exit /b 1
)

rem --- Instalar dependencias ---
echo Instalando dependencias (esto puede tardar unos minutos)...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet >nul 2>&1
".venv\Scripts\python.exe" -m pip install -e . --quiet >nul 2>&1
if errorlevel 1 (
    echo 1 > ".nexa_install_failed"
    echo 1 > ".nexa_install_done"
    exit /b 1
)

rem --- Indicar que la instalacion termino bien ---
echo 1 > ".nexa_install_done"
echo Instalacion completada. Iniciando NEXA...
timeout /t 2 /nobreak >nul

rem --- Lanzar la aplicacion ---
:launch
start "" ".venv\Scripts\pythonw.exe" -m hub.app
exit /b 0
