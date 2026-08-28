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
import socket
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    QCoreApplication,
    QObject,
    QProcess,
    QThread,
    Signal as QSignal,
)

from hub.models.plugin import PluginDescriptor

logger = logging.getLogger(__name__)

# Subcarpeta dentro de %APPDATA%\NEXA\ProductivityHub donde se instalan/descubren
# los binarios de las herramientas externas.
_APP_DIR_NAME = "apps"

# Timeout de red para descargas/copias desde recursos remotos.
_NET_TIMEOUT_S = 15
# Timeout máximo de espera durante una instalación sincrónica de un binario.
_INSTALL_WAIT_MS = 25000


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
            socket.setdefaulttimeout(_NET_TIMEOUT_S)
            dest = self._resolve_destination()
            if dest is None:
                self.failed.emit("No se pudo determinar el destino del binario.")
                return
            dest = self._fetch(dest)
            self.done.emit(True, str(dest), "Herramienta instalada correctamente.")
        except Exception as e:  # noqa: BLE001
            logger.exception("Error instalando herramienta externa")
            self.failed.emit(str(e))

    def _resolve_destination(self) -> Path | None:
        try:
            self._dest_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None
        exe = self._plugin.executable_name or f"{self._plugin.id}.exe"
        return self._dest_dir / Path(exe).name

    def _fetch(self, dest: Path) -> Path:
        # 1) Rutas/URLs de origen configuradas en el manifest
        sources: list[str] = []
        for p in self._plugin.launch_paths or []:
            if p:
                sources.append(p)
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
            except Exception as e:  # noqa: BLE001
                last_err = e
                logger.warning("No se pudo instalar desde '%s': %s", src, e)
        raise RuntimeError(f"No se pudo instalar la herramienta. Último error: {last_err}")

    def _copy_from_local(self, src: str, dest: Path) -> None:
        src_path = Path(src).expanduser()
        if not src_path.is_file():
            raise FileNotFoundError(f"Archivo no encontrado en ruta local: {src_path}")
        Path(dest.parent).mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest)

    def _copy_from_network(self, src: str, dest: Path) -> None:
        from urllib import request
        import urllib.parse

        if src.startswith("\\\\") or src.startswith("smb://"):
            path = src.replace("smb://", "\\\\").replace("/", "\\")
            self._copy_from_local(path, dest)
            return
        if src.startswith("file://"):
            url = urllib.parse.urlparse(src).path
            self._copy_from_local(url, dest)
            return
        Path(dest.parent).mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        try:
            with request.urlopen(url=src, timeout=_NET_TIMEOUT_S) as resp, open(tmp, "wb") as f:  # noqa: S310
                shutil.copyfileobj(resp, f)
            if tmp.is_file() and tmp.stat().st_size > 0:
                tmp.replace(dest)
            else:
                raise RuntimeError("Descarga vacía o incompleta.")
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass


class AppLauncherService(QObject):
    """Localiza e inicia herramientas externas de forma aislada.

    Emite install_finished(plugin_id, ok, mensaje) desde el hilo principal
    cuando una instalación en segundo plano termina.
    """

    install_finished = QSignal(str, bool, str)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._processes: dict[str, QProcess] = {}
        self._workers: dict[str, _DownloadWorker] = {}
        self._apps_dir = _apps_dir()

    # ------------------------------------------------------------------
    def apps_dir(self) -> Path:
        return self._apps_dir

    def installed_path(self, plugin: PluginDescriptor) -> Path | None:
        """Ruta local ya instalada del binario, si existe."""
        exe = plugin.executable_name or f"{plugin.id}.exe"
        candidates = [self._apps_dir / Path(exe).name]
        for p in plugin.launch_paths or []:
            pp = Path(p).expanduser()
            if pp.suffix.lower() == ".exe":
                candidates.append(pp)
        for cand in candidates:
            try:
                if cand.is_file():
                    return cand
            except OSError:
                continue
        return None

    def is_installed(self, plugin: PluginDescriptor) -> bool:
        if not plugin.is_external:
            return True
        return self.installed_path(plugin) is not None

    def is_running(self, plugin: PluginDescriptor) -> bool:
        proc = self._processes.get(plugin.id)
        return bool(proc and proc.state() in (
            QProcess.ProcessState.Starting,
            QProcess.ProcessState.Running,
        ))

    # ------------------------------------------------------------------
    def launch(self, plugin: PluginDescriptor) -> tuple[bool, str]:
        """Lanza el ejecutable externo. Devuelve (ok, mensaje)."""
        if not plugin.is_external:
            return False, "Esta herramienta no se lanza como proceso externo."

        path = self.installed_path(plugin)
        if path is None:
            ok, msg = self.install(plugin, block=True)
            if not ok:
                return False, (
                    "No se pudo abrir la aplicación.\n"
                    "No se encontró el binario y no se pudo descargar.\n"
                    f"Detalle: {msg}"
                )
            path = self.installed_path(plugin)
            if path is None:
                return False, "Se instaló el binario pero no se encontró en disco."

        # Reutilizar ventana si ya está abierta
        existing = self._processes.get(plugin.id)
        if existing and existing.state() == QProcess.ProcessState.Running:
            return True, "La aplicación ya se encuentra abierta."

        proc = QProcess()
        proc.setProgram(str(path))
        proc.finished.connect(lambda _c, _s, p=proc: self._on_finished(plugin.id, p))
        proc.errorOccurred.connect(lambda err, p=proc: self._on_error(plugin.id, err))
        self._processes[plugin.id] = proc
        try:
            proc.start()
        except Exception as e:  # noqa: BLE001
            logger.exception("Error arrancando proceso externo %s", plugin.id)
            self._processes.pop(plugin.id, None)
            return False, f"El binario no pudo iniciarse: {e}"
        return True, f"Abriendo {path.name}..."

    # ------------------------------------------------------------------
    def install(self, plugin: PluginDescriptor, block: bool = False) -> tuple[bool, str]:
        """Instala/copia el binario externo a la carpeta local de apps.

        - block=False: lanza la descarga en un hilo de fondo y devuelve de inmediato.
        - block=True: espera un tiempo acotado el resultado (recomendado para UI).
        """
        if not plugin.is_external:
            return False, "La herramienta no requiere instalación (modo embebido)."
        try:
            self._apps_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return False, f"No se pudo crear la carpeta de apps: {e}"

        worker = _DownloadWorker(plugin, self._apps_dir, self.parent())
        self._workers[plugin.id] = worker
        worker.done.connect(lambda ok, dest, msg, w=worker: self._release_worker(plugin.id, w))
        worker.failed.connect(lambda err, w=worker: self._release_worker(plugin.id, w))

        if not block:
            worker.start()
            return True, "Descargando herramienta en segundo plano..."

        # Espera acotada para conocer el resultado antes de seguir (UI friendly).
        # No depende de la cola de eventos, así funciona también sin QCoreApplication.
        worker.start()
        deadline = time.monotonic() + _INSTALL_WAIT_MS / 1000.0
        while worker.isRunning() and time.monotonic() < deadline:
            app = QCoreApplication.instance()
            if app is not None:
                app.processEvents()  # En la UI, mantiene la interfaz viva durante la espera.
            QThread.msleep(10)

        if worker.isRunning():
            worker.requestInterruption()
            worker.wait(2000)
            return False, "La descarga tardó demasiado. Comprueba la conexión de red."

        dest = worker._resolve_destination()
        ok = bool(dest and dest.is_file())
        return ok, (str(dest) if ok else "No se pudo instalar el binario (revisa rutas/red).")

    # ------------------------------------------------------------------
    def install_async(self, plugin: PluginDescriptor) -> bool:
        """Inicia la descarga en segundo plano y emite install_finished al terminar.

        No bloquea la UI. Devuelve False si no se pudo iniciar la instalación
        (y no se emitirá ninguna señal).
        """
        if not plugin.is_external:
            return False
        try:
            self._apps_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.install_finished.emit(plugin.id, False, f"No se pudo crear la carpeta de apps: {e}")
            return True
        worker = _DownloadWorker(plugin, self._apps_dir, self)
        self._workers[plugin.id] = worker
        worker.done.connect(lambda ok, dest, msg, w=worker, pid=plugin.id: self._on_worker_done(pid, w, ok, msg))
        worker.failed.connect(lambda err, w=worker, pid=plugin.id: self._on_worker_failed(pid, w, err))
        worker.start()
        return True

    def _on_worker_done(self, plugin_id: str, worker: _DownloadWorker, ok: bool, msg: str) -> None:
        self._release_worker(plugin_id, worker)
        self.install_finished.emit(plugin_id, bool(ok), msg)

    def _on_worker_failed(self, plugin_id: str, worker: _DownloadWorker, err: str) -> None:
        self._release_worker(plugin_id, worker)
        self.install_finished.emit(plugin_id, False, str(err))

    def _release_worker(self, plugin_id: str, worker: _DownloadWorker) -> None:
        if self._workers.get(plugin_id) is worker:
            self._workers.pop(plugin_id, None)

    # ------------------------------------------------------------------
    def _on_finished(self, plugin_id: str, proc: QProcess) -> None:
        self._processes.pop(plugin_id, None)
        logger.info("Proceso externo terminado: %s", plugin_id)

    def _on_error(self, plugin_id: str, err) -> None:
        logger.warning("Error lanzando '%s': %s", plugin_id, err)

    def close(self) -> None:
        for worker in list(self._workers.values()):
            try:
                if worker.isRunning():
                    worker.requestInterruption()
                    worker.wait(1500)
            except Exception:  # noqa: BLE001
                pass
        self._workers.clear()
        for proc in list(self._processes.values()):
            try:
                if proc.state() != QProcess.ProcessState.NotRunning:
                    proc.kill()
            except Exception:  # noqa: BLE001
                pass
        self._processes.clear()