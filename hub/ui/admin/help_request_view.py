"""UI — Help Request View. Formulario 'Tengo un problema' con auto-búsqueda."""

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
    NEXAStyles, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, get_font,
)


class HelpRequestView(QWidget):
    """Formulario para que el usuario solicite ayuda con una tarea repetitiva."""

    submitted = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("\U0001f198 Tengo un problema")
        header.setFont(get_font(20, bold=True))
        header.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(header)

        subtitle = QLabel("Cuéntanos qué necesitas hacer y te ayudaremos a encontrar una solución.")
        subtitle.setFont(get_font(12))
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY};")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        form = QFrame()
        form.setStyleSheet(NEXAStyles.card())
        form_layout = QVBoxLayout(form)
        form_layout.setSpacing(12)

        self._fields: dict[str, QWidget] = {}
        field_defs = [
            ("what", "¿Qué necesitas hacer?", "text"),
            ("time", "¿Cuánto tiempo te demora?", "text"),
            ("frequency", "¿Con qué frecuencia lo haces?", "text"),
            ("people", "¿Cuántas personas realizan esta tarea?", "text"),
            ("tools", "¿Qué herramientas utilizas?", "text"),
        ]
        for key, label_text, _ in field_defs:
            lbl = QLabel(label_text)
            lbl.setFont(get_font(12, bold=True))
            lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
            form_layout.addWidget(lbl)
            inp = QLineEdit()
            inp.setFont(get_font(12))
            inp.setStyleSheet(NEXAStyles.search_input())
            inp.setPlaceholderText(label_text)
            form_layout.addWidget(inp)
            self._fields[key] = inp

        lbl = QLabel("Describe el proceso")
        lbl.setFont(get_font(12, bold=True))
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        form_layout.addWidget(lbl)
        self._description = QTextEdit()
        self._description.setFont(get_font(12))
        self._description.setPlaceholderText("Describe paso a paso qué haces...")
        self._description.setMaximumHeight(100)
        form_layout.addWidget(self._description)
        self._fields["description"] = self._description

        layout.addWidget(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        submit_btn = QPushButton("\U0001f4e4  Enviar Solicitud")
        submit_btn.setStyleSheet(NEXAStyles.primary_button())
        submit_btn.setFixedWidth(200)
        submit_btn.clicked.connect(self._on_submit)
        btn_row.addWidget(submit_btn)
        layout.addLayout(btn_row)

        self._result_frame = QFrame()
        self._result_frame.setStyleSheet(NEXAStyles.card())
        self._result_frame.setVisible(False)
        result_layout = QVBoxLayout(self._result_frame)
        self._result_label = QLabel("")
        self._result_label.setFont(get_font(12))
        self._result_label.setWordWrap(True)
        self._result_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        result_layout.addWidget(self._result_label)
        layout.addWidget(self._result_frame)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _on_submit(self) -> None:
        data = {}
        for key, widget in self._fields.items():
            if isinstance(widget, QTextEdit):
                data[key] = widget.toPlainText().strip()
            else:
                data[key] = widget.text().strip()
        self.submitted.emit(data)
        self._result_label.setText(
            "\u2705 Solicitud enviada. Buscaremos herramientas que puedan ayudarte."
        )
        self._result_frame.setVisible(True)

    def show_suggestion(self, plugin_name: str, plugin_id: str) -> None:
        self._result_label.setText(
            f"Encontramos que la herramienta \u00ab{plugin_name}\u00bb podría ayudarte."
        )
        self._result_frame.setVisible(True)
