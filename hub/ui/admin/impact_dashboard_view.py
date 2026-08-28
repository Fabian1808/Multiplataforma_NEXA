"""UI — Impact Dashboard View. Métricas de productividad e impacto."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hub.ui.common.design import (
    Theme,
    NEXAStyles,
    ACCENT,
    Icon,
    SUCCESS,
    WARNING,
    get_font
)


class ImpactDashboardView(QWidget):
    """Dashboard administrativo de métricas e impacto."""

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
        header_icon = Icon("chart", 20)
        header_icon.set_color(ACCENT)
        header_row.addWidget(header_icon)
        header = QLabel("Dashboard de Impacto")
        header.setFont(get_font(20, bold=True))
        header.setStyleSheet(f"color: {Theme.text()};")
        header_row.addWidget(header, stretch=1)
        layout.addLayout(header_row)

        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(16)
        self._kpi_cards: dict[str, QLabel] = {}
        kpis = [
            ("users", "users", "Usuarios Activos", "0", ACCENT),
            ("tools", "apps", "Herramientas", "0", "#1565C0"),
            ("executions", "play", "Ejecuciones", "0", SUCCESS),
            ("hours_saved", "clock", "Horas Ahorradas", "0 h", WARNING),
            ("requests", "list", "Solicitudes", "0", "#6A1B9A"),
            ("knowledge", "book", "Artículos KB", "0", "#00838F"),
        ]
        for i, (key, icon, title, value, color) in enumerate(kpis):
            card = self._create_kpi_card(icon, title, value, color)
            kpi_grid.addWidget(card, i // 3, i % 3)
            self._kpi_cards[key] = card.findChild(QLabel, "kpi_value")
        layout.addLayout(kpi_grid)

        sections_grid = QGridLayout()
        sections_grid.setSpacing(16)

        impact_frame = QFrame()
        impact_frame.setStyleSheet(NEXAStyles.card())
        impact_layout = QVBoxLayout(impact_frame)
        impact_title = QLabel("Impacto Estimado")
        impact_title.setFont(get_font(14, bold=True))
        impact_layout.addWidget(impact_title)
        self._impact_value = QLabel("S/ 0.00")
        self._impact_value.setFont(get_font(24, bold=True))
        self._impact_value.setStyleSheet(f"color: {SUCCESS};")
        impact_layout.addWidget(self._impact_value)
        self._impact_detail = QLabel("Horas ahorradas × costo hora-hombre")
        self._impact_detail.setFont(get_font(10))
        self._impact_detail.setStyleSheet(f"color: {Theme.text_muted()};")
        impact_layout.addWidget(self._impact_detail)
        sections_grid.addWidget(impact_frame, 0, 0)

        status_frame = QFrame()
        status_frame.setStyleSheet(NEXAStyles.card())
        status_layout = QVBoxLayout(status_frame)
        status_title = QLabel("Estado de Herramientas")
        status_title.setFont(get_font(14, bold=True))
        status_layout.addWidget(status_title)
        self._status_labels: dict[str, QLabel] = {}
        for status_name, color in [("operational", SUCCESS), ("warning", WARNING), ("error", "#D32F2F")]:
            row = QHBoxLayout()
            dot = QLabel("\u25cf")
            dot.setFont(get_font(14))
            dot.setStyleSheet(f"color: {color};")
            dot.setFixedWidth(20)
            row.addWidget(dot)
            lbl = QLabel(f"{status_name.capitalize()}: 0")
            lbl.setFont(get_font(11))
            row.addWidget(lbl)
            row.addStretch()
            status_layout.addLayout(row)
            self._status_labels[status_name] = lbl
        sections_grid.addWidget(status_frame, 0, 1)

        top_plugins_frame = QFrame()
        top_plugins_frame.setStyleSheet(NEXAStyles.card())
        top_layout = QVBoxLayout(top_plugins_frame)
        top_title = QLabel("Top Herramientas")
        top_title.setFont(get_font(14, bold=True))
        top_layout.addWidget(top_title)
        self._top_plugins_list = QVBoxLayout()
        top_layout.addLayout(self._top_plugins_list)
        sections_grid.addWidget(top_plugins_frame, 1, 0, 1, 2)

        layout.addLayout(sections_grid)
        layout.addStretch()

        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _create_kpi_card(self, icon: str, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {color}10;
                border: 1px solid {color}30;
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(4)

        ico = Icon(icon, 20)
        ico.set_color(color)
        layout.addWidget(ico, alignment=Qt.AlignmentFlag.AlignLeft)

        title_lbl = QLabel(title)
        title_lbl.setFont(get_font(11))
        title_lbl.setStyleSheet(f"color: {Theme.text_secondary()};")
        layout.addWidget(title_lbl)

        value_lbl = QLabel(value)
        value_lbl.setObjectName("kpi_value")
        value_lbl.setFont(get_font(22, bold=True))
        value_lbl.setStyleSheet(f"color: {color};")
        layout.addWidget(value_lbl)

        return card

    def update_kpi(self, key: str, value: str) -> None:
        if key in self._kpi_cards:
            self._kpi_cards[key].setText(value)

    def update_impact(self, amount: str) -> None:
        self._impact_value.setText(amount)

    def update_health(self, summary: dict[str, int]) -> None:
        for status, count in summary.items():
            if status in self._status_labels:
                self._status_labels[status].setText(f"{status.capitalize()}: {count}")

    def set_top_plugins(self, plugins: list[tuple[str, int]]) -> None:
        while self._top_plugins_list.count():
            item = self._top_plugins_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for name, count in plugins:
            row = QHBoxLayout()
            name_lbl = QLabel(name)
            name_lbl.setFont(get_font(11))
            name_lbl.setStyleSheet(f"color: {Theme.text()};")
            row.addWidget(name_lbl, stretch=1)
            count_lbl = QLabel(f"{count} ejecuciones")
            count_lbl.setFont(get_font(11))
            count_lbl.setStyleSheet(f"color: {Theme.text_muted()};")
            row.addWidget(count_lbl)
            container = QWidget()
            container.setLayout(row)
            self._top_plugins_list.addWidget(container)
