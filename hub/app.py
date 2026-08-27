"""NEXA Productivity Hub — Entry Point con ServiceContainer."""

from __future__ import annotations

import ctypes
import logging
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QLabel, QMainWindow, QProgressBar,
    QSplashScreen, QStackedWidget, QVBoxLayout, QWidget,
)

from hub import __app_name__, __version__
from hub.core.service_container import ServiceContainer
from hub.infrastructure.logging_setup import setup_logging
from hub.ui.auth.login_view import LoginView
from hub.ui.common.design import Theme
from hub.ui.shell import Shell

logger = logging.getLogger(__name__)

# Nombre del mutex de instancia única.
# IMPORTANTE: En Python "Global\\" produce un doble backslash literal que
# Windows rechaza con ERROR_INVALID_NAME (123). Se usa nombre simple sin
# namespace para máxima compatibilidad entre sesiones de usuario.
MUTEX_NAME = "NEXA_Productivity_Hub_SingleInstance"


# ---------------------------------------------------------------------------
# Splash Screen
# ---------------------------------------------------------------------------
class NexaSplash(QSplashScreen):
    """Pantalla de carga con logo, barra de progreso y mensajes de estado."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
        )
        self.resize(480, 300)

        # Widget central
        widget = QWidget(self)
        widget.setGeometry(0, 0, 480, 300)
        widget.setStyleSheet(
            "background-color: #1E1E2E; border-radius: 16px;"
        )
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(48, 40, 48, 32)
        layout.setSpacing(12)

        # Logo
        logo = QLabel("⚡ NEXA")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font_logo = QFont("Segoe UI", 36, QFont.Weight.Bold)
        logo.setFont(font_logo)
        logo.setStyleSheet("color: #FF5503; background: transparent;")
        layout.addWidget(logo)

        # Subtítulo
        sub = QLabel("Productivity Hub")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setFont(QFont("Segoe UI", 13))
        sub.setStyleSheet("color: #A0A0B8; background: transparent;")
        layout.addWidget(sub)

        layout.addStretch()

        # Mensaje de estado
        self._status_lbl = QLabel("Iniciando...")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setFont(QFont("Segoe UI", 10))
        self._status_lbl.setStyleSheet("color: #6E6E88; background: transparent;")
        layout.addWidget(self._status_lbl)

        # Barra de progreso
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        self._bar.setStyleSheet(
            "QProgressBar { background: #3D3D55; border-radius: 3px; border: none; }"
            "QProgressBar::chunk { background: #FF5503; border-radius: 3px; }"
        )
        layout.addWidget(self._bar)

        # Versión
        ver = QLabel(f"v{__version__}")
        ver.setAlignment(Qt.AlignmentFlag.AlignRight)
        ver.setFont(QFont("Segoe UI", 9))
        ver.setStyleSheet("color: #3D3D55; background: transparent;")
        layout.addWidget(ver)

        self._center_on_screen()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.center().x() - self.width() // 2,
                geo.center().y() - self.height() // 2,
            )

    def set_status(self, message: str, progress: int) -> None:
        self._status_lbl.setText(message)
        self._bar.setValue(progress)
        QApplication.processEvents()




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

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Cierra la BD y limpia recursos al cerrar la ventana principal."""
        try:
            self._services.close()
        except Exception:
            logger.exception("Error al cerrar ServiceContainer")
        super().closeEvent(event)


def create_app() -> QApplication:
    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")

    # Mostrar splash inmediatamente — el usuario ve algo en <0.3s
    splash = NexaSplash()
    splash.show()
    splash.set_status("Conectando base de datos...", 20)

    # La MainWindow inicializa ServiceContainer (DB + servicios)
    splash.set_status("Cargando servicios...", 45)
    window = MainWindow()

    splash.set_status("Preparando interfaz...", 75)
    window.show()

    splash.set_status("Listo ✓", 100)
    # Cerrar splash con pequeño delay para que se vea el 100%
    QTimer.singleShot(350, splash.close)

    return app


def main() -> None:
    setup_logging()
    logger.info("Iniciando %s v%s", __app_name__, __version__)

    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = ctypes.windll.kernel32.GetLastError()

    if mutex == 0:
        # CreateMutexW falló completamente (handle nulo).
        # Continuamos sin protección de instancia única para no bloquear el arranque.
        logger.warning(
            "No se pudo crear el mutex de instancia única (error=%d). "
            "Se permite continuar sin control de instancia.",
            last_error,
        )
        mutex = None
    elif last_error == 183:  # ERROR_ALREADY_EXISTS
        logger.warning("Otra instancia ya está corriendo — abortando.")
        ctypes.windll.kernel32.CloseHandle(mutex)
        sys.exit(0)

    try:
        app = create_app()
        sys.exit(app.exec())
    except Exception:
        logger.exception("Error fatal durante la inicialización")
        sys.exit(1)
    finally:
        if mutex:
            ctypes.windll.kernel32.ReleaseMutex(mutex)
            ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
