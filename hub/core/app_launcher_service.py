"""Core — App Launcher Service.

Implementa la estrategia HÍBRIDA de ejecución de herramientas:

  - "embedded": la herramienta es un widget Qt dentro del hub (modo por defecto).
  - "external": la herramienta es un ejecutable independiente que se lanza como
    un proceso aparte. El hub localiza el binario en:
      a) rutas locales configuradas (launch_paths),
      b) ubicación por red interna / URL (launch_url), donde se puede descargar
         o copiar una versión actualizada.

De esta forma las herramientas pesadas (Horas Extras, SAP) no congelan el hub,
llevan sus propias dependencias y se actualizan de forma independiente.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

from PySide6.QtCore import QProcess, QThread, Signal as QSignal

from hub.models.plugin import PluginDescriptor

logger = logging.getLogger(__name__)

# Subcarpeta dentro de %APPDATA%\NEXA\ProductivityHub donde se instalan/descubren
# los binarios de las herramientas externas.
_APP_DIR_NAME = "apps"


def _apps_dir() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home()))
    return Path(appdata) / "NEXA" / "ProductivityHub" / _APP_DIR_NAME


class _DownloadWorker(QThread):
    """Descarga/copia el binario de una herramienta externa en segundo plano."""

    done = QSignal(bool, str, str)  # (ok, ruta_destino, mensaje)
    failed = QSignal(str)

    def __init__(self, plugin: PluginDescriptor, dest_dir: Path, parent=None):
        super().__init__(parent)
        self._plugin = plugin
        self._dest_dir = dest_dir

    def run(self) -> None:
        try:
            dest = self._resolve_destination()
            if dest is None:
                self.failed.emit("No se pudo determinar el destino del binario.")
                return
            dest = self._fetch(dest)
            self.done.emit(True, str(dest), "Herramienta instalada correctamente.")
        except Exception as e:
            logger.exception("Error instalando herramienta externa")
            self.failed.emit(str(e))

    def _resolve_destination(self) -> Path | None:
        self._dest_dir.mkdir(parents=True, exist_ok=True)
        exe = self._plugin.executable_name or f"{self._plugin.id}.exe"
        return self._dest_dir / Path(exe).name

    def _fetch(self, dest: Path) -> Path:
        # 1) Rutas/URLs de origen configuradas en el manifest
        sources: list[str] = list(self._plugin.launch_paths or [])
        if self._plugin.launch_url:
            sources.append(self._plugin.launch_url)
        if not sources:
            raise RuntimeError("Herramienta externa sin launch_paths / launch_url configurados.")

        last_err: Exception | None = None
        for src in sources:
            try:
                if src.lower().startswith(("http://", "https://", "file://", "smb://", "\\\\")):
                    self._copy_from_network(src, dest)
                else:
                    self._copy_from_local(src, dest)
                logger.info("Herramienta '%s' instalada desde %s -> %s", self._plugin.id, src, dest)
                return dest
            except Exception as e:
                last_err = e
                logger.warning("No se pudo instalar desde '%s': %s", src, e)
        raise RuntimeError(f"No se pudo instalar la herramienta. Último error: {last_err}")

    def _copy_from_local(self, src: str, dest: Path) -> None:
        src_path = Path(src).expanduser()
        if not src_path.is_file():
            raise FileNotFoundError(f"Archivo no encontrado en ruta local: {src_path}")
        shutil.copy2(src_path, dest)

    def _copy_from_network(self, src: str, dest: Path) -> None:
        from urllib import request
        import urllib.parse

        if src.startswith("\\\\") or src.startswith("smb://"):
            path = src.replace("smb://", "\\\\").replace("/", "\\")
            self._copy_from_local(path, dest)
            return
        url = src
        if src.startswith("file://"):
            url = urllib.parse.urlparse(src).path
            self._copy_from_local(url, dest)
            return
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        request.urlretrieve(url, tmp)  # noqa: S310
        tmp.replace(dest)


class AppLauncherService:
    """Localiza e inicia herramientas externas de forma aislada."""

    def __init__(self, parent: Any = None) -> None:
        self._parent = parent
        self._processes: dict[str, QProcess] = {}
        self._apps_dir = _apps_dir()

    # ------------------------------------------------------------------
    def apps_dir(self) -> Path:
        return self._apps_dir

    def installed_path(self, plugin: PluginDescriptor) -> Path | None:
        """Ruta local ya instalada del binario, si existe."""
        exe = plugin.executable_name or f"{plugin.id}.exe"
        candidates = []
        candidates.append(self._apps_dir / Path(exe).name)
        for p in plugin.launch_paths or []:
            pp = Path(p).expanduser()
            if pp.suffix.lower() == ".exe":
                candidates.append(pp)
        for cand in candidates:
            if cand.is_file():
                return cand
        return None

    def is_installed(self, plugin: PluginDescriptor) -> bool:
        if not plugin.is_external:
            return True
        return self.installed_path(plugin) is not None

    def is_running(self, plugin: PluginDescriptor) -> bool:
        proc = self._processes.get(plugin.id)
        return proc is not None and proc.state() not in (
            QProcess.ProcessState.NotRunning,
            QProcess.ProcessState.Starting,
        ) or (proc is not None and proc.state() == QProcess.ProcessState.Running)

    def launch(self, plugin: PluginDescriptor) -> tuple[bool, str]:
        """Lanza el ejecutable externo. Devuelve (ok, mensaje)."""
        if not plugin.is_external:
            return False, "Esta herramienta no se lanza como proceso externo."

        path = self.installed_path(plugin)
        if path is None:
            ok, msg = self.install(plugin)
            if not ok:
                return False, msg
            path = self.installed_path(plugin)
            if path is None:
                return False, "Se instalaría pero no se encontró el binario."

        # Reutilizar ventana si ya está abierta
        existing = self._processes.get(plugin.id)
        if existing and existing.state() == QProcess.ProcessState.Running:
            return True, "La aplicación ya se encuentra abierta."

        proc = QProcess(self._parent)
        proc.setProgram(str(path))
        proc.finished.connect(lambda _c, _s: self._on_finished(plugin.id, proc))
        proc.errorOccurred.connect(lambda err: self._on_error(plugin.id, err))
        self._processes[plugin.id] = proc
        proc.start()
        return True, f"Abriendo {path.name}..."

    def install(self, plugin: PluginDescriptor, block: bool = False) -> tuple[bool, str]:
        """Instala/copia el binario externo a la carpeta local de apps.

        Si block=False lanza la descarga en un hilo y devuelve (True, 'descargando').
        """
        self._apps_dir.mkdir(parents=True, exist_ok=True)
        if not block:
            worker = _DownloadWorker(plugin, self._apps_dir, self._parent)
            worker.failed.connect(
                lambda err: logger.warning("Instalación externa falló: %s", err))
            worker.start()
            return True, "Descargando herramienta..."
        # bloqueante (para test)
        exe = plugin.executable_name or f"{plugin.id}.exe"
        dest = self._apps_dir / Path(exe).name
        worker = _DownloadWorker(plugin, self._apps_dir)
        worker.run()
        return dest.is_file(), str(dest)

    def _on_finished(self, plugin_id: str, proc: QProcess) -> None:
        self._processes.pop(plugin_id, None)
        logger.info("Proceso externo terminado: %s", plugin_id)

    def _on_error(self, plugin_id: str, err) -> None:
        logger.warning("Error lanzando '%s': %s", plugin_id, err)
