"""UI — Automation Proposal View. Formulario 'Proponer automatización' con scoring."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hub.models.request import AutomationScore
from hub.ui.common.design import (
    NEXAStyles, ACCENT, SUCCESS, WARNING, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, get_font, Icon,
)


class AutomationProposalView(QWidget):
    """Formulario para proponer una nueva automatización con cálculo de impacto."""

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

        header_row = QHBoxLayout()
        header_icon = Icon("wrench", 20)
        header_icon.set_color(ACCENT)
        header_row.addWidget(header_icon)
        header = QLabel("Proponer Automatización")
        header.setFont(get_font(20, bold=True))
        header.setStyleSheet(f"color: {TEXT_PRIMARY};")
        header_row.addWidget(header, stretch=1)
        layout.addLayout(header_row)

        subtitle = QLabel("Describe una tarea repetitiva y te ayudaremos a convertirla en una automatización.")
        subtitle.setFont(get_font(12))
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(subtitle)

        form = QFrame()
        form.setStyleSheet(NEXAStyles.card())
        form_layout = QVBoxLayout(form)
        form_layout.setSpacing(12)

        self._fields: dict[str, QWidget] = {}
        field_defs = [
            ("task", "Tarea", "ej: Consolidar 50 archivos Excel cada viernes"),
            ("frequency", "Frecuencia", "ej: Semanal, diaria, mensual"),
            ("time_per_execution", "Tiempo por ejecución", "ej: 2 horas"),
            ("people", "Personas involucradas", "ej: 5 personas del área de finanzas"),
            ("tools", "Herramientas utilizadas", "ej: Excel, Outlook, SharePoint"),
        ]
        for key, label_text, placeholder in field_defs:
            lbl = QLabel(label_text)
            lbl.setFont(get_font(12, bold=True))
            lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
            form_layout.addWidget(lbl)
            inp = QLineEdit()
            inp.setFont(get_font(12))
            inp.setStyleSheet(NEXAStyles.search_input())
            inp.setPlaceholderText(placeholder)
            form_layout.addWidget(inp)
            self._fields[key] = inp

        lbl = QLabel("Pasos del proceso")
        lbl.setFont(get_font(12, bold=True))
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        form_layout.addWidget(lbl)
        self._steps = QTextEdit()
        self._steps.setFont(get_font(12))
        self._steps.setPlaceholderText("1. Descargar archivos\n2. Consolidar\n3. Validar\n4. Enviar")
        self._steps.setMaximumHeight(80)
        form_layout.addWidget(self._steps)

        lbl = QLabel("Problemas actuales")
        lbl.setFont(get_font(12, bold=True))
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        form_layout.addWidget(lbl)
        self._problems = QTextEdit()
        self._problems.setFont(get_font(12))
        self._problems.setPlaceholderText("Describe los problemas o frustraciones actuales...")
        self._problems.setMaximumHeight(60)
        form_layout.addWidget(self._problems)
        layout.addWidget(form)

        scoring_frame = QFrame()
        scoring_frame.setStyleSheet(NEXAStyles.card())
        scoring_layout = QVBoxLayout(scoring_frame)
        scoring_layout.setSpacing(8)

        score_title = QLabel("Estimación de Impacto")
        score_title.setFont(get_font(14, bold=True))
        scoring_layout.addWidget(score_title)

        time_row = QHBoxLayout()
        time_lbl = QLabel("Horas semanales estimadas:")
        time_lbl.setFont(get_font(11))
        self._hours_slider = QSlider(Qt.Orientation.Horizontal)
        self._hours_slider.setRange(0, 40)
        self._hours_slider.setValue(2)
        self._hours_slider.valueChanged.connect(self._update_score)
        self._hours_label = QLabel("2 h/sem")
        self._hours_label.setFont(get_font(11, bold=True))
        self._hours_label.setStyleSheet(f"color: {ACCENT};")
        time_row.addWidget(time_lbl)
        time_row.addWidget(self._hours_slider, stretch=1)
        time_row.addWidget(self._hours_label)
        scoring_layout.addLayout(time_row)

        people_row = QHBoxLayout()
        people_lbl = QLabel("Personas involucradas:")
        people_lbl.setFont(get_font(11))
        self._people_slider = QSlider(Qt.Orientation.Horizontal)
        self._people_slider.setRange(1, 20)
        self._people_slider.setValue(1)
        self._people_slider.valueChanged.connect(self._update_score)
        self._people_label = QLabel("1")
        self._people_label.setFont(get_font(11, bold=True))
        self._people_label.setStyleSheet(f"color: {ACCENT};")
        people_row.addWidget(people_lbl)
        people_row.addWidget(self._people_slider, stretch=1)
        people_row.addWidget(self._people_label)
        scoring_layout.addLayout(people_row)

        self._score_result = QLabel("")
        self._score_result.setFont(get_font(14, bold=True))
        self._score_result.setStyleSheet(f"color: {TEXT_PRIMARY};")
        self._score_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scoring_layout.addWidget(self._score_result)

        self._score_detail = QLabel("")
        self._score_detail.setFont(get_font(11))
        self._score_detail.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._score_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scoring_layout.addWidget(self._score_detail)

        layout.addWidget(scoring_frame)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        submit_btn = QPushButton("Enviar Propuesta")
        submit_btn.setStyleSheet(NEXAStyles.primary_button())
        submit_btn.setFixedWidth(200)
        submit_btn.clicked.connect(self._on_submit)
        btn_row.addWidget(submit_btn)
        layout.addLayout(btn_row)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        self._update_score()

    def _update_score(self) -> None:
        hours = self._hours_slider.value()
        people = self._people_slider.value()
        self._hours_label.setText(f"{hours} h/sem")
        self._people_label.setText(str(people))

        score = AutomationScore(weekly_hours=hours, people_involved=people)
        score.calculate()

        if score.classification == "alta":
            color = "#D32F2F"
            label = "Alta oportunidad"
        elif score.classification == "media":
            color = WARNING
            label = "Media oportunidad"
        else:
            color = SUCCESS
            label = "Baja oportunidad"

        self._score_result.setText(f"\u25cf {label}")
        self._score_result.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold;")
        self._score_detail.setText(
            f"~{score.monthly_hours:.0f} h/mes · ~{score.yearly_hours:.0f} h/año · "
            f"{people} persona(s) · Score: {score.score:.1f}"
        )

    def _on_submit(self) -> None:
        data = {}
        for key, widget in self._fields.items():
            data[key] = widget.text().strip()
        data["steps"] = self._steps.toPlainText().strip()
        data["problems"] = self._problems.toPlainText().strip()
        data["weekly_hours"] = self._hours_slider.value()
        data["people"] = self._people_slider.value()
        score = AutomationScore(
            weekly_hours=data["weekly_hours"],
            people_involved=data["people"],
        )
        score.calculate()
        data["score"] = score.score
        data["classification"] = score.classification
        self.submitted.emit(data)
