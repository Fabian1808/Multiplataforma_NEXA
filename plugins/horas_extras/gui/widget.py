"""Plugin: Horas Extras — Wrapper Qt para el Hub."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
    QFrame,
    QProgressBar,
    QTextEdit,
)

from hub.ui.common.design import NEXAStyles, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, get_font


class HorasExtrasWidget(QWidget):
    """Widget Qt que envuelve el motor de Horas Extras para el Hub."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine_path = Path(__file__).resolve().parent.parent / "engine"
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = QLabel("Sistema de Horas Extras")
        header.setFont(get_font(18, bold=True))
        header.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(header)

        desc = QLabel(
            "Automatiza la revisión y validación de horas extras contra marcaciones RAINBOW.\n"
            "Detecta inconsistencias, genera trazabilidad y mide impacto económico."
        )
        desc.setFont(get_font(12))
        desc.setStyleSheet(f"color: {TEXT_SECONDARY};")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(8)

        upload_frame = QFrame()
        upload_frame.setStyleSheet(NEXAStyles.card())
        upload_layout = QVBoxLayout(upload_frame)
        upload_layout.setSpacing(12)

        upload_title = QLabel("\U0001f4c2 Cargar Archivos")
        upload_title.setFont(get_font(14, bold=True))
        upload_layout.addWidget(upload_title)

        self._consolidado_label = QLabel("Consolidado: No seleccionado")
        self._consolidado_label.setFont(get_font(11))
        upload_layout.addWidget(self._consolidado_label)
        btn_consolidado = QPushButton("Seleccionar Consolidado Excel")
        btn_consolidado.setStyleSheet(NEXAStyles.secondary_button())
        btn_consolidado.clicked.connect(self._select_consolidado)
        upload_layout.addWidget(btn_consolidado)

        self._rainbow_label = QLabel("RAINBOW: No seleccionado")
        self._rainbow_label.setFont(get_font(11))
        upload_layout.addWidget(self._rainbow_label)
        btn_rainbow = QPushButton("Seleccionar Relatorio RAINBOW")
        btn_rainbow.setStyleSheet(NEXAStyles.secondary_button())
        btn_rainbow.clicked.connect(self._select_rainbow)
        upload_layout.addWidget(btn_rainbow)

        layout.addWidget(upload_frame)

        actions_frame = QFrame()
        actions_frame.setStyleSheet(NEXAStyles.card())
        actions_layout = QHBoxLayout(actions_frame)

        self._process_btn = QPushButton("\u25b6  PROCESAR")
        self._process_btn.setStyleSheet(NEXAStyles.primary_button())
        self._process_btn.setFixedHeight(44)
        self._process_btn.clicked.connect(self._on_process)
        actions_layout.addWidget(self._process_btn)

        self._download_btn = QPushButton("\U0001f4e5  Descargar Excel")
        self._download_btn.setStyleSheet(NEXAStyles.secondary_button())
        self._download_btn.setFixedHeight(44)
        self._download_btn.setEnabled(False)
        self._download_btn.clicked.connect(self._on_download)
        actions_layout.addWidget(self._download_btn)

        layout.addWidget(actions_frame)

        result_frame = QFrame()
        result_frame.setStyleSheet(NEXAStyles.card())
        result_layout = QVBoxLayout(result_frame)
        result_title = QLabel("Resultado")
        result_title.setFont(get_font(14, bold=True))
        result_layout.addWidget(result_title)
        self._result_text = QTextEdit()
        self._result_text.setReadOnly(True)
        self._result_text.setFont(get_font(11))
        self._result_text.setMaximumHeight(150)
        self._result_text.setStyleSheet("border: none; background: transparent;")
        self._result_text.setPlaceholderText("Los resultados aparecerán aquí después de procesar...")
        result_layout.addWidget(self._result_text)
        layout.addWidget(result_frame)

        layout.addStretch()

        self._consolidado_path: str = ""
        self._rainbow_paths: list[str] = []

    def _select_consolidado(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Consolidado", "", "Excel (*.xlsx *.xlsm)"
        )
        if path:
            self._consolidado_path = path
            name = Path(path).name
            self._consolidado_label.setText(f"Consolidado: {name}")
            self._consolidado_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold;")

    def _select_rainbow(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar Relatorio RAINBOW", "", "Excel (*.xlsx *.xlsm)"
        )
        if paths:
            self._rainbow_paths = paths
            names = ", ".join(Path(p).name for p in paths)
            self._rainbow_label.setText(f"RAINBOW: {names}")
            self._rainbow_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold;")

    def _on_process(self) -> None:
        if not self._consolidado_path:
            QMessageBox.warning(self, "Archivos requeridos", "Selecciona un archivo consolidado.")
            return
        if not self._rainbow_paths:
            QMessageBox.warning(self, "Archivos requeridos", "Selecciona al menos un archivo RAINBOW.")
            return

        self._process_btn.setEnabled(False)
        self._process_btn.setText("Procesando...")
        self._result_text.setText("Procesando... por favor espera.")

        from PySide6.QtCore import QThread, Signal as QSignal

        class Worker(QThread):
            finished = QSignal(str)
            error = QSignal(str)

            def __init__(self, consolidado: str, rainbows: list[str], engine_path: Path) -> None:
                super().__init__()
                self._consolidado = consolidado
                self._rainbows = rainbows
                self._engine_path = engine_path

            def run(self) -> None:
                try:
                    src_path = self._engine_path / "src"
                    if str(src_path) not in sys.path:
                        sys.path.insert(0, str(src_path))

                    from main import ejecutar_para_gui
                    
                    config_path = self._engine_path.parent / "config" / "config.json"
                    if not config_path.exists():
                        # Respaldar con el config dentro de engine/config
                        config_path = self._engine_path / "config" / "config.json"

                    resultado, exito = ejecutar_para_gui(
                        config_ruta=str(config_path),
                        consolidado=self._consolidado,
                        relatorios=self._rainbows,
                    )
                    
                    if exito:
                        self.finished.emit(str(resultado))
                    else:
                        self.error.emit(str(resultado))
                except Exception as e:
                    self.error.emit(str(e))

        self._worker = Worker(self._consolidado_path, self._rainbow_paths, self._engine_path)
        self._worker.finished.connect(self._on_process_done)
        self._worker.error.connect(self._on_process_error)
        self._worker.start()

    def _on_process_done(self, result: str) -> None:
        self._process_btn.setEnabled(True)
        self._process_btn.setText("\u25b6  PROCESAR")
        self._result_text.setText(f"Proceso completado:\n{result}")
        
        import re
        match = re.search(r"EXCEL COMPLETADO LISTO:\s*(.+)", result)
        if match:
            self._last_output_excel = match.group(1).strip()
            self._download_btn.setEnabled(True)

    def _on_process_error(self, error: str) -> None:
        self._process_btn.setEnabled(True)
        self._process_btn.setText("\u25b6  PROCESAR")
        self._result_text.setText(f"Error:\n{error}")

    def _on_download(self) -> None:
        path = getattr(self, "_last_output_excel", None)
        if not path:
            return
            
        import shutil
        default_name = Path(path).name
        dest, _ = QFileDialog.getSaveFileName(
            self, "Guardar Excel Completado", default_name, "Excel (*.xlsx *.xlsm)"
        )
        if dest:
            try:
                shutil.copy2(path, dest)
                QMessageBox.information(self, "Éxito", f"Archivo guardado correctamente en:\n{dest}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar el archivo:\n{str(e)}")


def create_widget(parent: Any = None) -> QWidget:
    """Punto de entrada para el Hub — crea el widget del plugin."""
    return HorasExtrasWidget(parent)
