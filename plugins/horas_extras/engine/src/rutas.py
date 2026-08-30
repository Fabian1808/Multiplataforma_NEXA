"""Resolucion unica de rutas de la aplicacion (desarrollo vs. empaquetado).

Distribucion portable (v1.0.0):
  - El usuario final recibe una carpeta APLICATIVO_RAINBOW/ con el .exe y las
    carpetas Entrada/, Salida/, Config/ y Logs/ junto a el. Se copia a
    cualquier PC y funciona sin instalar nada (no hay rutas absolutas de un
    usuario en particular).
  - PROGRAMA (codigo, recursos, config por defecto): dentro del ejecutable
    (_MEIPASS en PyInstaller). Se reemplaza completo en cada actualizacion.
  - DATOS del usuario (config editable, preferencias, historial, logs,
    resultados, actualizaciones): junto al .exe. Nunca se borran al
    actualizar (se reemplaza solo el .exe) y viajan con la carpeta.
  - Desarrollo: mismas carpetas del proyecto que usaba la app historicamente
    (BASE_DATOS = app/), para no cambiar el comportamiento actual.

Uso:
    from rutas import BASE_DATOS, CONFIG_RUTA, ...
    garantizar_base_datos()   # crea carpetas y copia el config base si falta
"""

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

EMPAQUETADO = bool(getattr(sys, "_MEIPASS", None))

if EMPAQUETADO:
    ROOT = Path(sys._MEIPASS)
    BASE_APP = Path(sys.executable).resolve().parent
else:
    ROOT = Path(__file__).resolve().parent.parent
    BASE_APP = ROOT

APP_DIR = ROOT / "app"
ASSETS = ROOT / "app" / "assets"

# Config por defecto (empaquetado dentro del .exe; es SOLO lectura).
CONFIG_DEFECTO = ROOT / "config" / "config.json"

# Carpeta de datos del usuario: junto al .exe (portable) o app/ (desarrollo).
BASE_DATOS = BASE_APP if EMPAQUETADO else APP_DIR

# Config editable del usuario: en desarrollo es el config del proyecto
# (igual que siempre); empaquetado, una copia en Config/ creada en el
# primer arranque a partir de CONFIG_DEFECTO.
CONFIG_DIR = BASE_APP / "Config" if EMPAQUETADO else ROOT / "config"
CONFIG_RUTA = CONFIG_DIR / "config.json"

PREFERENCIAS = BASE_APP / "Config" / "preferencias.json" if EMPAQUETADO \
    else BASE_DATOS / "preferencias.json"
HISTORIAL = BASE_APP / "Logs" / "historial_errores.json" if EMPAQUETADO \
    else BASE_DATOS / "historial_errores.json"

# Logs: Logs/ en portable, app/logs/ en desarrollo.
DIR_LOG = BASE_APP / "Logs" if EMPAQUETADO else BASE_DATOS / "logs"
LOG_APP = DIR_LOG / "LOG_APP.csv"

# Carpetas del flujo de trabajo del usuario (portable).
DIR_ENTRADA_DEFECTO = BASE_APP / "Entrada"
DIR_SALIDA_DEFECTO = BASE_APP / "Salida" if EMPAQUETADO \
    else ROOT / "data" / "output"
DIR_DEMO = BASE_APP / "Salida" / "_demo" if EMPAQUETADO \
    else ROOT / "data" / "output_demo"

# Carpeta del actualizador (descargas, backups y estado).
DIR_ACTUALIZACIONES = BASE_APP / "Config" / "actualizaciones"
VERSION_APLICADA = DIR_ACTUALIZACIONES / "version_aplicada.json"


def ruta_log_diario():
    """Log diario de errores: Logs/aplicativo_YYYY-MM-DD.log (portable) o
    app/logs/aplicativo_YYYY-MM-DD.log (desarrollo)."""
    nombre = "aplicativo_%s.log" % datetime.now().strftime("%Y-%m-%d")
    return DIR_LOG / nombre


def garantizar_base_datos():
    """Crea la estructura de datos del usuario si falta (portable: junto al
    .exe; desarrollo: app/).

    En modo empaquetado copia el config por defecto del .exe a Config/ en el
    primer arranque (nunca sobrescribe un config existente del usuario).
    Devuelve True si todo quedó listo.
    """
    try:
        for carpeta in (BASE_DATOS, CONFIG_DIR, DIR_LOG, DIR_SALIDA_DEFECTO,
                        DIR_ENTRADA_DEFECTO, DIR_DEMO, DIR_ACTUALIZACIONES):
            carpeta.mkdir(parents=True, exist_ok=True)
        if EMPAQUETADO and not CONFIG_RUTA.exists() and CONFIG_DEFECTO.exists():
            shutil.copy2(str(CONFIG_DEFECTO), str(CONFIG_RUTA))
        return True
    except Exception:
        return False