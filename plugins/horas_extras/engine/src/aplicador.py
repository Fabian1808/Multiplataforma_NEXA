"""Aplicador de actualizaciones (proceso separado).

La app principal NO puede reemplazar su propio .exe: Windows bloquea el
archivo mientras el proceso esta en ejecucion. Este proceso (empaquetado
como 'Aplicativo_Rainbow_Updater.exe' junto a la app):

  1. Espera unos segundos a que la app principal termine.
  2. Ejecuta el instalador Inno en silencio (/VERYSILENT).
  3. Si la instalacion fue exitosa, relanza la app.
  4. Termina.

Uso (desde la app principal):
    Aplicativo_Rainbow_Updater.exe <Setup.exe> <ruta de la app>

Si la instalacion falla, el arranque siguiente detecta la marca
(version_aplicada.json) y aplica el rollback con el Setup de respaldo.
"""

import subprocess
import sys
import time


def main():
    if len(sys.argv) < 3:
        return 1
    setup, app = sys.argv[1], sys.argv[2]
    time.sleep(3)  # la app principal cierra su ventana y termina
    cmd = [setup, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-"]
    try:
        rc = subprocess.run(cmd, timeout=600).returncode
    except Exception:
        rc = 1
    if rc == 0:
        try:
            subprocess.Popen([app])
        except Exception:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main())