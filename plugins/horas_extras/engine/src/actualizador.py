"""Actualizador de NEXA - Control de Horas Extras.

Flujo de actualizacion (disenado en docs/ARQUITECTURA_DISTRIBUCION.md):

  Arranque -> verificar_arranque()          (recuperacion de intentos previos)
           -> verificar(manifest_url)       (consulta version.json en HTTPS)
           -> descargar() + SHA-256         (nunca se ejecuta un archivo corrupto)
           -> guardar_backup()              (Setup anterior para rollback)
           -> marcar_aplicado()             (registro de la version intentada)
           -> instalar_con_setup()          (Inno Setup en silencio)
           -> relanzar()

Recuperacion (si la actualizacion falla o la nueva version no arranca):
  - Si la marca dice otra version y existe el Setup de respaldo -> rollback
    (reinstala la version anterior y relanza).
  - Si no hay respaldo -> se borra la marca y se continua con la actual.
  - Si la version instalada coincide con la marca pero nunca se confirmo
    (fase "instalando" con marca antigua) -> tambien se restaura.

Seguridad:
  - HTTPS por defecto (config actualizacion.permitir_http=false).
  - SHA-256 del instalador verificado antes de ejecutarlo.
  - Nunca se descarga ni ejecuta codigo: solo el instalador verificado.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from rutas import DIR_ACTUALIZACIONES, VERSION_APLICADA, EMPAQUETADO, ROOT
from version import VERSION, comparar

NOMBRE_SETUP = "Aplicativo_Rainbow_Setup_%s.exe"
DIR_BACKUP = DIR_ACTUALIZACIONES / "backup"
GRACIA_SEG = 60  # ventana para confirmar un arranque tras actualizar


class InfoActualizacion:
    """Version disponible segun el manifest (version.json)."""

    def __init__(self, version, url, sha256, obligatoria=False, notas=""):
        self.version = str(version)
        self.url = url
        self.sha256 = sha256
        self.obligatoria = bool(obligatoria)
        self.notas = notas or ""

    @classmethod
    def desde_manifest(cls, datos):
        """Valida el manifest y construye la informacion; lanza ValueError si
        falta un campo obligatorio o la version no es semver."""
        if not isinstance(datos, dict):
            raise ValueError("manifest invalido")
        version = datos.get("version")
        url = datos.get("url")
        sha256 = datos.get("sha256")
        if not version or not url or not sha256:
            raise ValueError("manifest incompleto (version/url/sha256)")
        comparar(version, "0.0.0")  # valida semver
        return cls(version, url, sha256,
                   obligatoria=datos.get("obligatoria", False),
                   notas=datos.get("notas", ""))

    def __repr__(self):
        return "<InfoActualizacion %s obligatoria=%s>" % (self.version,
                                                          self.obligatoria)


def _solicitud(url, permitir_http=False, agente="NEXA-Updater/1.0"):
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("URL invalida: %r" % (url,))
    if url.lower().startswith("http://") and not permitir_http:
        raise ValueError("URL insegura (http) y permitir_http=false")
    return urllib.request.Request(url, headers={"User-Agent": agente})


def verificar(manifest_url, version_actual=None, timeout=10, permitir_http=False):
    """Consulta el manifest y devuelve InfoActualizacion si hay una version
    nueva; None si no la hay, si el manifest es invalido o si no hay red.

    Nunca lanza excepciones hacia la GUI: los fallos de red son silenciosos
    (la aplicacion debe seguir funcionando sin conexion).
    """
    version_actual = version_actual or VERSION
    try:
        req = _solicitud(manifest_url, permitir_http)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            datos = json.loads(resp.read().decode("utf-8"))
        info = InfoActualizacion.desde_manifest(datos)
    except Exception:
        return None
    if comparar(info.version, version_actual) <= 0:
        return None
    return info


def sha256_de_archivo(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def descargar(info, destino_dir=None, progreso=None):
    """Descarga el instalador a destino_dir y verifica su SHA-256.

    Devuelve la ruta del archivo verificado. Lanza ValueError si el hash no
    coincide (el archivo temporal se elimina) o excepciones de red. El
    destino nunca se corrompe: primero .tmp, luego rename.
    """
    destino_dir = Path(destino_dir or DIR_ACTUALIZACIONES)
    destino_dir.mkdir(parents=True, exist_ok=True)
    tmp = destino_dir / (NOMBRE_SETUP % info.version + ".tmp")
    final = destino_dir / (NOMBRE_SETUP % info.version)
    req = _solicitud(info.url, permitir_http=True)  # el http se evalua al verificar el manifest
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as fh:
            while True:
                bloque = resp.read(65536)
                if not bloque:
                    break
                fh.write(bloque)
                if progreso:
                    progreso(len(bloque))
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    h = sha256_de_archivo(tmp)
    if h.lower() != str(info.sha256).lower():
        tmp.unlink(missing_ok=True)
        raise ValueError("Hash no coincide: esperado %s, obtenido %s"
                         % (info.sha256, h))
    tmp.replace(final)
    return final


def guardar_backup(setup_anterior, dir_backup=None):
    """Guarda el Setup ANTERIOR (si existe y aun no esta respaldado) para
    poder revertir la actualizacion."""
    if not setup_anterior or not Path(setup_anterior).exists():
        return
    dir_backup = Path(dir_backup or DIR_BACKUP)
    dir_backup.mkdir(parents=True, exist_ok=True)
    destino = dir_backup / Path(setup_anterior).name
    if not destino.exists():
        shutil.copy2(str(setup_anterior), str(destino))


def setup_cacheado(version, dir_actualizaciones=None):
    return Path(dir_actualizaciones or DIR_ACTUALIZACIONES) / (NOMBRE_SETUP % version)


def instalar_con_setup(setup, esperar=True, timeout=600):
    """Ejecuta el instalador Inno en silencio. Devuelve el codigo de salida
    (si esperar=True) o None."""
    cmd = [str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-"]
    if esperar:
        proc = subprocess.run(cmd, timeout=timeout)
        return proc.returncode
    subprocess.Popen(cmd)
    return None


def marcar_aplicado(version, fase="instalando", ruta_estado=None):
    """Registra la version que se intenta instalar (y su fase)."""
    ruta_estado = Path(ruta_estado or VERSION_APLICADA)
    ruta_estado.parent.mkdir(parents=True, exist_ok=True)
    datos = {"version": str(version), "fase": fase,
             "fecha": datetime.now().isoformat(timespec="seconds")}
    with open(ruta_estado, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2)


def confirmar_arranque(version=None, ruta_estado=None):
    """La app confirma que arranco bien tras una actualizacion (fase ok)."""
    marcar_aplicado(version or VERSION, fase="ok",
                    ruta_estado=ruta_estado or VERSION_APLICADA)


def borrar_marca(ruta_estado=None):
    ruta_estado = Path(ruta_estado or VERSION_APLICADA)
    try:
        ruta_estado.unlink()
    except Exception:
        pass


def verificar_arranque(version_actual=None, ruta_estado=None, dir_backup=None):
    """Estado de recuperacion al arrancar la aplicacion.

    Devuelve:
      "ok"          no hay marca, o la marca coincide y esta confirmada.
      "confirmar"   la marca coincide con la version actual pero en fase
                    "instalando" y es reciente -> la app se confirma sola.
      "rollback"    una actualizacion quedo a medias o la nueva version no
                    arranco: hay Setup de respaldo para restaurar.
      "continuar"   quedó a medias pero no hay respaldo -> se borra la marca
                    y se continua con la version actual.
    """
    version_actual = version_actual or VERSION
    ruta_estado = Path(ruta_estado or VERSION_APLICADA)
    if not ruta_estado.exists():
        return "ok"
    try:
        with open(ruta_estado, encoding="utf-8") as fh:
            marca = json.load(fh)
    except Exception:
        borrar_marca(ruta_estado)
        return "continuar"
    marcada = str(marca.get("version", ""))
    fase = str(marca.get("fase", ""))
    try:
        fecha = datetime.fromisoformat(str(marca.get("fecha", "")))
    except Exception:
        fecha = datetime.min
    respaldo = Path(dir_backup or DIR_BACKUP)
    hay_respaldo = respaldo.exists() and any(respaldo.glob("Setup_*.exe"))

    if comparar(marcada, version_actual) == 0:
        if fase == "ok":
            return "ok"
        reciente = (datetime.now() - fecha).total_seconds() <= GRACIA_SEG
        if reciente:
            return "confirmar"
        borrar_marca(ruta_estado)
        return "rollback" if hay_respaldo else "continuar"
    # la marca apunta a otra version: la actualizacion no tomo efecto
    borrar_marca(ruta_estado)
    return "rollback" if hay_respaldo else "continuar"


def relanzar():
    """Relanza la aplicacion (el .exe empaquetado o la GUI en desarrollo)."""
    if EMPAQUETADO:
        subprocess.Popen([sys.executable])
    else:
        subprocess.Popen([sys.executable, str(ROOT / "app" / "gui.py")])


def ejecutar_actualizacion(info, progreso=None):
    """Prepara la actualizacion completa (descarga + verificacion + backup +
    marca). Devuelve la ruta del Setup verificado.

    El paso de INSTALACION lo ejecuta 'Aplicativo_Rainbow_Updater.exe' (proceso
    separado) porque Windows bloquea el .exe de la app en ejecucion. La GUI
    llama a lanzar_aplicador() y se cierra. Si algo falla aqui se lanza la
    excepcion (el intento queda registrado; verificar_arranque hara el rollback).
    """
    setup_nuevo = descargar(info, progreso=progreso)
    anterior = setup_cacheado(VERSION)
    guardar_backup(anterior)
    marcar_aplicado(info.version, fase="instalando")
    return setup_nuevo


def ruta_aplicador():
    """Ruta de 'Aplicativo_Rainbow_Updater.exe' (vive junto al .exe principal)."""
    if not EMPAQUETADO:
        return None
    return Path(sys.executable).parent / "Aplicativo_Rainbow_Updater.exe"


def lanzar_aplicador(setup, app=None):
    """Lanza el proceso aplicador (instala y relanza) y devuelve True."""
    aplicador = ruta_aplicador()
    if not aplicador or not aplicador.exists():
        raise RuntimeError("El aplicador de actualizaciones no esta disponible")
    subprocess.Popen([str(aplicador), str(setup), app or sys.executable])
    return True


# Solo para pruebas manuales rapidas: python -m actualizador <url_manifest>
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--permitir-http", action="store_true")
    args = parser.parse_args()
    info = verificar(args.url, permitir_http=args.permitir_http)
    if not info:
        print("Sin actualizaciones disponibles (o sin red).")
        raise SystemExit(0)
    print("Nueva version: %s (obligatoria=%s)" % (info.version, info.obligatoria))
    print("Notas: %s" % info.notas)