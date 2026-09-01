"""NEXA Productivity Hub — Entry Point con ServiceContainer."""

from __future__ import annotations

import ctypes
import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QLabel, QMainWindow, QProgressBar,
    QSplashScreen, QStackedWidget, QVBoxLayout, QWidget,
)

from hub import __app_name__, __version__
from hub.core.service_container import ServiceContainer
from hub.i18n import tr
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

_APP_ICON: QIcon | None = None
_APP_ICON_READ = False


def _app_icon() -> QIcon | None:
    """Ícono de la aplicación (assets/logo_taskbar.png), cargo perezoso."""
    global _APP_ICON, _APP_ICON_READ
    if not _APP_ICON_READ:
        _APP_ICON_READ = True
        p = Path(__file__).resolve().parent / "assets" / "logo_taskbar.png"
        if p.is_file():
            try:
                _APP_ICON = QIcon(str(p))
            except Exception:
                logger.exception("No se pudo cargar el ícono de la aplicación")
    return _APP_ICON


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
        logo = QLabel("NEXA")
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
        self._status_lbl = QLabel(tr("splash.starting"))
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
        try:
            self._shell = Shell(self._services)
            self._shell.setup_ui(user_data)
            self._shell.logout_requested.connect(self._on_logout)
            self._stack.addWidget(self._shell)
            self._stack.setCurrentWidget(self._shell)
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.exception("CRITICAL ERROR IN LOGIN SUCCESS")
            import sys
            sys.exit(1)


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
        QApplication.quit()
        super().closeEvent(event)


def create_app() -> tuple[QApplication, "MainWindow"]:
    # Fuerza renderizado por software para evitar crashes silenciosos de GPU
    # (Qt 6 + drivers/GPUs remotas o VM en esta máquina). Debe fijarse ANTES
    # de crear QApplication.
    if not os.environ.get("QT_QUICK_BACKEND"):
        os.environ["QT_QUICK_BACKEND"] = "software"
    if not os.environ.get("QT_OPENGL"):
        os.environ["QT_OPENGL"] = "software"
    if not os.environ.get("QT_OPENGL_SOFTWARE"):
        os.environ["QT_OPENGL_SOFTWARE"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")

    # Esperar hilos de trabajo de plugins (p.ej. cálculo/exportación de Horas
    # Extras Masiva) antes de cerrar: evita el abort fatal de Qt
    # "QThread: Destroyed while thread is still running" al salir con un
    # proceso en curso.
    def _esperar_hilos_al_cerrar() -> None:
        try:
            import importlib, os, sys as _sys
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            gui_dir = os.path.join(root, "plugins", "horas_extras_masiva", "gui")
            if os.path.isfile(os.path.join(gui_dir, "thread_registry.py")):
                if gui_dir not in _sys.path:
                    _sys.path.insert(0, gui_dir)
                importlib.import_module("thread_registry").esperar_hilos_activos()
        except Exception:
            pass

    app.aboutToQuit.connect(_esperar_hilos_al_cerrar)

    # Ícono de ventana/taskbar (logo con transparencia)
    icon = _app_icon()
    if icon is not None:
        app.setWindowIcon(icon)

    # Mostrar splash inmediatamente — el usuario ve algo en <0.3s
    splash = NexaSplash()
    splash.show()
    splash.set_status(tr("splash.db"), 20)

    # La MainWindow inicializa ServiceContainer (DB + servicios)
    splash.set_status(tr("splash.services"), 45)
    window = MainWindow()

    splash.set_status(tr("splash.ui"), 75)
    window.show()

    splash.set_status(tr("splash.ready"), 100)
    # Cerrar splash con pequeño delay para que se vea el 100%
    QTimer.singleShot(350, splash.close)

    return app, window


def main() -> None:
    setup_logging()
    logger.info("Iniciando %s v%s", __app_name__, __version__)

    # Excepción global no capturada (FASE 8): se registra en el log para
    # diagnóstico y se muestra un aviso no bloqueante al usuario en lugar de
    # terminar en silencio o cerrarse a medias.
    def _excepthook(exc_type, exc, tb):
        logger.critical("Excepción no capturada", exc_info=(exc_type, exc, tb))
        try:
            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QApplication, QMessageBox

            def _mostrar():
                dlg = QMessageBox(QMessageBox.Icon.Critical, "Error inesperado",
                                  "Ocurrió un error inesperado.\n\n"
                                  "Los detalles ya quedaron registrados.\n\n" + str(exc))
                dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
                dlg.exec()

            app = QApplication.instance()
            if app is not None:
                QTimer.singleShot(0, _mostrar)
            else:
                _mostrar()
        except Exception:
            pass

    sys.excepthook = _excepthook

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
        logger.warning(
            "Otra instancia ya está corriendo — abortando. "
            "Si no ves la ventana, cierra cualquier proceso 'nexa-hub' o "
            "'python -m hub.app' pendiente y reintenta."
        )
        ctypes.windll.kernel32.CloseHandle(mutex)
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                "NEXA Productivity Hub ya está abierto.\n\n"
                "Si no ves la ventana, revisa la barra de tareas o el área de notificaciones.",
                "NEXA Productivity Hub",
                0x40,  # MB_ICONINFORMATION | MB_OK
            )
        except Exception:
            pass
        sys.exit(0)

    try:
        import signal

        def _sig(signum, frame):
            logger.warning("CHK: recibida señal %s — frame=%s", signum, frame)
            sys.exit(128 + signum)

        for _sig_name in ("SIGINT", "SIGTERM", "SIGHUP", "SIGBREAK"):
            _s = getattr(signal, _sig_name, None)
            if _s is not None:
                try:
                    signal.signal(_s, _sig)
                except Exception:
                    pass

        app, window = create_app()

        rc = app.exec()
        sys.exit(rc if isinstance(rc, int) else 0)
    except Exception:
        logger.exception("Error fatal durante la inicialización")
        sys.exit(1)
    finally:
        if mutex:
            ctypes.windll.kernel32.ReleaseMutex(mutex)
            ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
