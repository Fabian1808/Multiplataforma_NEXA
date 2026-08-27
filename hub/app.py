"""NEXA Productivity Hub — Entry Point con ServiceContainer."""

from __future__ import annotations

import ctypes
import logging
import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from hub import __app_name__, __version__
from hub.core.service_container import ServiceContainer
from hub.infrastructure.logging_setup import setup_logging
from hub.ui.auth.login_view import LoginView
from hub.ui.common.design import Theme
from hub.ui.shell import Shell

logger = logging.getLogger(__name__)

MUTEX_NAME = "Global\\NEXA_Productivity_Hub_SingleInstance"


class MainWindow(QMainWindow):
    """Top-level window that manages login <-> shell transitions."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.setMinimumSize(1024, 680)
        self.resize(1280, 800)

        self._services = ServiceContainer()

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._shell: Shell | None = None

        self._show_login()

    def _show_login(self) -> None:
        login = LoginView(self._services.auth)
        login.login_success.connect(self._on_login_success)
        self._stack.addWidget(login)
        self._stack.setCurrentWidget(login)

    def _on_login_success(self, user_data: dict) -> None:
        self._shell = Shell(self._services)
        self._shell.setup_ui(user_data)
        self._shell.logout_requested.connect(self._on_logout)
        self._stack.addWidget(self._shell)
        self._stack.setCurrentWidget(self._shell)

    def _on_logout(self) -> None:
        if self._shell is not None:
            self._shell.logout_requested.disconnect()
            self._stack.removeWidget(self._shell)
            self._shell.deleteLater()
            self._shell = None
        self._show_login()


def create_app() -> QApplication:
    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app


def main() -> None:
    setup_logging()
    logger.info("Iniciando %s v%s", __app_name__, __version__)

    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:
        logger.warning("Otra instancia ya está corriendo — abortando.")
        sys.exit(0)

    try:
        app = create_app()
        sys.exit(app.exec())
    except Exception:
        logger.exception("Error fatal durante la inicialización")
        sys.exit(1)
    finally:
        ctypes.windll.kernel32.ReleaseMutex(mutex)
        ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
