# Desarrollo — NEXA Productivity Hub

Guía de operación del repositorio para trabajar en otro equipo (p. ej. en casa).

## Requisitos

- Windows 10/11 (se usa `%APPDATA%` y mutex de Win32).
- **Python 3.11+** en el PATH.
- Git.

## Instalación

```bat
:: Desde la raíz del repositorio:
Instalar_NEXA.bat
```

El script crea el entorno `.venv` (si no existe) y ejecuta
`.venv\Scripts\python.exe -m pip install -e .`.

Equivalente manual:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"   # para pytest, ruff, mypy
```

Dependencias (definidas en `pyproject.toml`): `PySide6>=6.8`, `openpyxl`,
`pywin32`, `Pillow`, `PyYAML`; dev: `pytest`, `pytest-cov`, `pytest-mock`,
`ruff`, `mypy`.

## Ejecutar

```bat
Iniciar_NEXA.bat          :: lanza .venv\Scripts\pythonw.exe -m hub.app
```

O desde consola (con salida visible en terminal):

```powershell
.\.venv\Scripts\python.exe -m hub.app
```

- Run única instancia: si ya hay una abierta, la segunda muestra un
  MessageBoxW informativo y termina.
- El ícono de ventana/taskbar se carga de `assets/logo_taskbar.png`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q        # suite completa (86 tests)
.\.venv\Scripts\python.exe -m pytest tests\unit
.\.venv\Scripts\python.exe -m pytest tests\smoke
```

Comprobación rápida de sintaxis:

```powershell
.\.venv\Scripts\python.exe -m py_compile hub\ui\shell.py hub\ui\common\design.py hub\app.py
```

## Compilar ejecutable

```bat
Construir_Ejecutable.bat
```

Genera con PyInstaller en modo `--onedir --windowed` usando el spec
`NEXA_Productivity_Hub.spec`, que:
- incluye la carpeta `assets/` como datos (`datas=[('assets', 'assets')]`);
- asigna el ícono `assets/logo_taskbar.ico` al ejecutable.

(Existe además `nexa_hub.spec`, spec antiguo sin assets; no usar para el build actual.)

## Rutas en disco (runtime)

| Concepto | Ruta |
|---|---|
| Base de datos | `%APPDATA%\NEXA\ProductivityHub\data\nexus.db` |
| Preferencia de tema | `%APPDATA%\NEXA\ProductivityHub\theme.json` |
| Logs | `%APPDATA%\NEXA\ProductivityHub\logs\` |
| Apps externas | `%APPDATA%\NEXA\ProductivityHub\apps\` |

## Operación del tema

- `hub\ui\common\design.py` mantiene el estado global del tema
  (`set_theme()`/`get_theme()`/`save_theme()`) y lo persiste en `theme.json`.
- El sidebar alterna el tema con el botón ☀/🌙 en su panel inferior;
  `hub\ui\shell.py` re-aplica paletas y QSS dinámicamente
  (`apply_theme`/`_refresh_sidebar_static`).

## Advertencias de plataforma

- **PowerShell 5.1** no soporta `&&`: encadenar con `cmd1; if ($?) { cmd2 }`.
- Los archivos con acentos se guardan **UTF-8**; si Git reporta cambios de
  final de línea (LF→CRLF), es ruido normal y no debe commitearse si no hay
  cambios reales.
- Para pruebas de UI sin monitor se puede usar Qt offscreen:
  `$env:QT_QPA_PLATFORM="offscreen"` antes de ejecutar `pytest`/scripts.