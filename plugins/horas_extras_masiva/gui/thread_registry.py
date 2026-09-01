"""Registro global de hilos de trabajo activos del plugin.

Módulo pequeño y sin dependencias pesadas (ni QtCharts, ni hub.UI) para que
`hub/app.py` pueda importarlo de forma segura al salir de la aplicación y
esperar a que terminen los QThread de cálculo/exportación antes de destruirlos.

Uso:
    from thread_registry import registrar_thread, desregistrar_thread
    registrar_thread(self._worker)

    # En aboutToQuit de la app:
    from thread_registry import esperar_hilos_activos
    esperar_hilos_activos()
"""

from __future__ import annotations

from threading import Lock

_ACTIVE_THREADS: set = set()
_LOCK = Lock()


def registrar_thread(th) -> None:
    with _LOCK:
        _ACTIVE_THREADS.add(th)


def desregistrar_thread(th) -> None:
    with _LOCK:
        _ACTIVE_THREADS.discard(th)


def esperar_hilos_activos(timeout_ms: int = 10000) -> None:
    """Espera a que todos los hilos de trabajo registrados terminen."""
    with _LOCK:
        items = list(_ACTIVE_THREADS)
    for th in items:
        if th.isRunning():
            th.wait(timeout_ms)