"""Plugin: SAP Automation — Wrapper Qt para el Hub."""

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
    QTextEdit,
    QPlainTextEdit,
)

from hub.ui.common.design import NEXAStyles, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, get_font


class SAPAutomationWidget(QWidget):
    """Widget Qt que envuelve el módulo SAP HES para el Hub."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sap_path = Path(__file__).resolve().parent.parent
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = QLabel("Automatización SAP")
        header.setFont(get_font(18, bold=True))
        header.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(header)

        desc = QLabel(
            "Automatiza tareas repetitivas en SAP GUI: descarga masiva de documentos HES,\n"
            "ejecución de macros VBS y gestión de órdenes de compra."
        )
        desc.setFont(get_font(12))
        desc.setStyleSheet(f"color: {TEXT_SECONDARY};")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(8)

        input_frame = QFrame()
        input_frame.setStyleSheet(NEXAStyles.card())
        input_layout = QVBoxLayout(input_frame)
        input_layout.setSpacing(12)

        input_title = QLabel("\U0001f4cb Documentos SAP")
        input_title.setFont(get_font(14, bold=True))
        input_layout.addWidget(input_title)

        input_desc = QLabel("Ingresa los números de documento (uno por línea):")
        input_desc.setFont(get_font(11))
        input_layout.addWidget(input_desc)

        self._doc_input = QPlainTextEdit()
        self._doc_input.setPlaceholderText("1000001\n1000002\n1000003")
        self._doc_input.setFont(get_font(11))
        self._doc_input.setMaximumHeight(100)
        self._doc_input.setStyleSheet(NEXAStyles.search_input())
        input_layout.addWidget(self._doc_input)

        layout.addWidget(input_frame)

        actions_frame = QFrame()
        actions_frame.setStyleSheet(NEXAStyles.card())
        actions_layout = QHBoxLayout(actions_frame)

        self._run_btn = QPushButton("\u25b6  EJECUTAR EN SAP")
        self._run_btn.setStyleSheet(NEXAStyles.primary_button())
        self._run_btn.setFixedHeight(44)
        self._run_btn.clicked.connect(self._on_run)
        actions_layout.addWidget(self._run_btn)

        self._status_btn = QPushButton("\U0001f50c  Verificar Conexión SAP")
        self._status_btn.setStyleSheet(NEXAStyles.secondary_button())
        self._status_btn.setFixedHeight(44)
        self._status_btn.clicked.connect(self._on_check_status)
        actions_layout.addWidget(self._status_btn)

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
        self._result_text.setPlaceholderText("Los resultados aparecerán aquí...")
        result_layout.addWidget(self._result_text)
        layout.addWidget(result_frame)

        layout.addStretch()

    def _on_run(self) -> None:
        docs = self._doc_input.toPlainText().strip()
        if not docs:
            QMessageBox.warning(self, "Documentos requeridos", "Ingresa al menos un número de documento.")
            return

        self._run_btn.setEnabled(False)
        self._run_btn.setText("Ejecutando...")
        self._result_text.setText("Conectando con SAP GUI...")

        self._result_text.setText(
            "Módulo SAP HES disponible.\n"
            "Para ejecutar la automatización completa, usa la aplicación standalone "
            "o intégra el módulo HES como sub-plugin.\n\n"
            "Documentos ingresados:\n" + docs
        )
        self._run_btn.setEnabled(True)
        self._run_btn.setText("\u25b6  EJECUTAR EN SAP")

    def _on_check_status(self) -> None:
        try:
            import win32com.client
            sap = win32com.client.GetObject("SAPGUI")
            self._result_text.setText("\u2705 Conexión SAP GUI detectada correctamente.")
        except Exception:
            self._result_text.setText(
                "\u274c No se pudo detectar SAP GUI.\n"
                "Verifica que SAP GUI esté abierto y configurado."
            )


def create_widget(parent: Any = None) -> QWidget:
    """Punto de entrada para el Hub — crea el widget del plugin."""
    return SAPAutomationWidget(parent)
