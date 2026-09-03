"""UI — Issue Report View. Reportar problemas con herramientas."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hub.ui.common.design import (
    Theme,
    NEXAStyles,
    ACCENT,
    Icon,
    get_font
)


class IssueReportView(QWidget):
    """Formulario para reportar problemas con herramientas."""

    submitted = Signal(dict)

    def __init__(self, plugin_name: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._plugin_name = plugin_name
        self._setup_ui()

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self._label_refs: list[QLabel] = []
        header_row = QHBoxLayout()
        header_icon = Icon("flag", 20)
        header_icon.set_color(ACCENT)
        header_row.addWidget(header_icon)
        self._header = QLabel("Reportar Problema")
        self._header.setFont(get_font(20, bold=True))
        self._header.setStyleSheet(f"color: {Theme.text()};")
        header_row.addWidget(self._header, stretch=1)
        layout.addLayout(header_row)

        self._subtitle = QLabel("Describe el problema que encontraste para que podamos solucionarlo.")
        self._subtitle.setFont(get_font(12))
        self._subtitle.setStyleSheet(f"color: {Theme.text_secondary()};")
        self._label_refs.append(self._subtitle)
        layout.addWidget(self._subtitle)

        self._form = QFrame()
        self._form.setStyleSheet(NEXAStyles.card())
        form_layout = QVBoxLayout(self._form)
        form_layout.setSpacing(12)

        if self._plugin_name:
            lbl = QLabel(f"Herramienta: {self._plugin_name}")
            lbl.setFont(get_font(12, bold=True))
            lbl.setStyleSheet(f"color: {Theme.text()};")
            self._label_refs.append(lbl)
            form_layout.addWidget(lbl)

        self._fields: dict[str, QWidget] = {}
        field_defs = [
            ("title", "Título del problema", "text"),
            ("tool", "Herramienta afectada", "text"),
            ("expected", "¿Qué esperabas que pasara?", "text"),
        ]
        for key, label_text, _ in field_defs:
            lbl = QLabel(label_text)
            lbl.setFont(get_font(12, bold=True))
            lbl.setStyleSheet(f"color: {Theme.text()};")
            self._label_refs.append(lbl)
            form_layout.addWidget(lbl)
            inp = QLineEdit()
            inp.setFont(get_font(12))
            inp.setStyleSheet(NEXAStyles.search_input())
            form_layout.addWidget(inp)
            self._fields[key] = inp

        lbl = QLabel("¿Qué pasó en realidad?")
        lbl.setFont(get_font(12, bold=True))
        lbl.setStyleSheet(f"color: {Theme.text()};")
        self._label_refs.append(lbl)
        form_layout.addWidget(lbl)
        self._what_happened = QTextEdit()
        self._what_happened.setFont(get_font(12))
        self._what_happened.setPlaceholderText("Describe el problema con detalle...")
        self._what_happened.setMaximumHeight(100)
        form_layout.addWidget(self._what_happened)

        lbl = QLabel("Pasos para reproducir (opcional)")
        lbl.setFont(get_font(12, bold=True))
        lbl.setStyleSheet(f"color: {Theme.text()};")
        self._label_refs.append(lbl)
        form_layout.addWidget(lbl)
        self._steps = QTextEdit()
        self._steps.setFont(get_font(12))
        self._steps.setPlaceholderText("1. Abrí la herramienta\n2. Cargué el archivo\n3. Error...")
        self._steps.setMaximumHeight(80)
        form_layout.addWidget(self._steps)

        layout.addWidget(self._form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._submit_btn = QPushButton("Enviar Reporte")
        self._submit_btn.setStyleSheet(NEXAStyles.primary_button())
        self._submit_btn.setFixedWidth(200)
        self._submit_btn.clicked.connect(self._on_submit)
        btn_row.addWidget(self._submit_btn)
        layout.addLayout(btn_row)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def refresh_style(self) -> None:
        """Re-aplica el tema activo (claro/oscuro) al formulario de reporte."""
        self.setStyleSheet(f"QWidget {{ background-color: {Theme.bg()}; color: {Theme.text()}; }}")
        self._header.setStyleSheet(f"color: {Theme.text()};")
        for lbl in self._label_refs:
            if lbl is self._subtitle:
                lbl.setStyleSheet(f"color: {Theme.text_secondary()};")
            else:
                lbl.setStyleSheet(f"color: {Theme.text()};")
        self._form.setStyleSheet(NEXAStyles.card())
        for widget in self._fields.values():
            widget.setStyleSheet(NEXAStyles.search_input())
        self._what_happened.setStyleSheet(NEXAStyles.text_edit())
        self._steps.setStyleSheet(NEXAStyles.text_edit())
        self._submit_btn.setStyleSheet(NEXAStyles.primary_button())

    def _on_submit(self) -> None:
        data = {}
        for key, widget in self._fields.items():
            data[key] = widget.text().strip()
        data["what_happened"] = self._what_happened.toPlainText().strip()
        data["steps"] = self._steps.toPlainText().strip()
        self.submitted.emit(data)
