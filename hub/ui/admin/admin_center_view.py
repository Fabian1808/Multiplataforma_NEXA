"""UI — Admin Center. Gestión centralizada de la plataforma."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hub.core.health_check import HealthCheckService
from hub.models.plugin import PluginDescriptor
from hub.ui.common.design import (
    NEXAStyles, ACCENT, SUCCESS, WARNING, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, get_font, Icon,
)

_PAGE_APPS = 0
_PAGE_HEALTH = 1
_PAGE_OPPORTUNITIES = 2


class AdminCenterView(QWidget):
    """Centro de administración de la plataforma."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        nav = QWidget()
        nav.setFixedWidth(200)
        nav.setStyleSheet(f"background-color: {TEXT_PRIMARY};")
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(8, 16, 8, 16)
        nav_layout.setSpacing(4)

        title = QLabel("Admin Center")
        title.setFont(get_font(14, bold=True))
        title.setStyleSheet("color: #FFFFFF;")
        nav_layout.addWidget(title)
        nav_layout.addSpacing(12)

        self._nav_buttons: list[QPushButton] = []
        nav_items = [
            ("Herramientas", _PAGE_APPS),
            ("Health Check", _PAGE_HEALTH),
            ("Oportunidades", _PAGE_OPPORTUNITIES),
        ]
        for label, page in nav_items:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 12px;
                    text-align: left;
                    font-size: 12px;
                }
                QPushButton:hover { background-color: #555555; }
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, p=page, b=btn: self._navigate(p, b))
            nav_layout.addWidget(btn)
            self._nav_buttons.append(btn)
        nav_layout.addStretch()
        main_layout.addWidget(nav)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._create_apps_page())
        self._stack.addWidget(self._create_health_page())
        self._stack.addWidget(self._create_opportunities_page())
        main_layout.addWidget(self._stack, stretch=1)

    def _create_apps_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Gestión de Herramientas")
        header.setFont(get_font(18, bold=True))
        header.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self._apps_grid = QGridLayout(content)
        self._apps_grid.setSpacing(12)
        self._apps_grid.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)
        return page

    def _create_health_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Health Check de Herramientas")
        header.setFont(get_font(18, bold=True))
        header.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(header)

        self._health_list = QVBoxLayout()
        self._health_list.setSpacing(8)
        layout.addLayout(self._health_list)
        layout.addStretch()
        return page

    def _create_opportunities_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Búsquedas sin Resultado")
        header.setFont(get_font(18, bold=True))
        header.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(header)

        subtitle = QLabel("Estas búsquedas indican herramientas que los usuarios necesitan pero no existen.")
        subtitle.setFont(get_font(12))
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(subtitle)

        self._opportunities_list = QVBoxLayout()
        self._opportunities_list.setSpacing(8)
        layout.addLayout(self._opportunities_list)
        layout.addStretch()
        return page

    def _navigate(self, page: int, active_btn: QPushButton) -> None:
        self._stack.setCurrentIndex(page)
        for btn in self._nav_buttons:
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 12px;
                    text-align: left;
                    font-size: 12px;
                }
                QPushButton:hover { background-color: #555555; }
            """)
        active_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5503;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px 12px;
                text-align: left;
                font-size: 12px;
            }
        """)

    def set_plugins(self, plugins: list[PluginDescriptor]) -> None:
        while self._apps_grid.count():
            item = self._apps_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, plugin in enumerate(plugins):
            card = QFrame()
            card.setStyleSheet(NEXAStyles.card())
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(4)

            name_row = QHBoxLayout()
            name = QLabel(plugin.name)
            name.setFont(get_font(12, bold=True))
            name.setStyleSheet(f"color: {TEXT_PRIMARY};")
            name_row.addWidget(name, stretch=1)
            status_color = SUCCESS if plugin.status.value == "oficial" else WARNING if plugin.status.value == "beta" else TEXT_MUTED
            status_lbl = QLabel(plugin.status.value.capitalize())
            status_lbl.setFont(get_font(10))
            status_lbl.setStyleSheet(f"color: {status_color};")
            name_row.addWidget(status_lbl)
            card_layout.addLayout(name_row)

            meta = QLabel(f"v{plugin.version} · Owner: {plugin.owner} · {plugin.execution_count} ejecuciones")
            meta.setFont(get_font(10))
            meta.setStyleSheet(f"color: {TEXT_MUTED};")
            card_layout.addWidget(meta)

            self._apps_grid.addWidget(card, i // 2, i % 2)

    def set_health_reports(self, reports: dict) -> None:
        while self._health_list.count():
            item = self._health_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for plugin_id, report in reports.items():
            card = QFrame()
            card.setStyleSheet(NEXAStyles.card())
            card_layout = QHBoxLayout(card)
            card_layout.setSpacing(12)

            status_colors = {"operational": SUCCESS, "warning": WARNING, "error": "#D32F2F"}
            color = status_colors.get(report.status, TEXT_MUTED)
            dot = QLabel("\u25cf")
            dot.setFont(get_font(18))
            dot.setStyleSheet(f"color: {color};")
            card_layout.addWidget(dot)

            info = QVBoxLayout()
            info.setSpacing(2)
            name_lbl = QLabel(plugin_id)
            name_lbl.setFont(get_font(12, bold=True))
            name_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
            info.addWidget(name_lbl)
            msg_lbl = QLabel(report.message)
            msg_lbl.setFont(get_font(10))
            msg_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
            info.addWidget(msg_lbl)
            card_layout.addLayout(info, stretch=1)
            self._health_list.addWidget(card)

    def set_opportunities(self, opportunities: list[dict]) -> None:
        while self._opportunities_list.count():
            item = self._opportunities_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not opportunities:
            empty = QLabel("No hay búsquedas sin resultado registradas.")
            empty.setFont(get_font(12))
            empty.setStyleSheet(f"color: {TEXT_MUTED}; padding: 20px;")
            self._opportunities_list.addWidget(empty)
            return

        for opp in opportunities:
            card = QFrame()
            card.setStyleSheet(NEXAStyles.card())
            card_layout = QHBoxLayout(card)

            query_icon = Icon("search", 15)
            query_icon.set_color(TEXT_MUTED)
            card_layout.addWidget(query_icon)
            query_lbl = QLabel(f"\"{opp['query']}\"")
            query_lbl.setFont(get_font(12, bold=True))
            query_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
            card_layout.addWidget(query_lbl, stretch=1)

            count_lbl = QLabel(f"{opp['occurrences']} busqueda(s)")
            count_lbl.setFont(get_font(11))
            count_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
            card_layout.addWidget(count_lbl)

            self._opportunities_list.addWidget(card)
