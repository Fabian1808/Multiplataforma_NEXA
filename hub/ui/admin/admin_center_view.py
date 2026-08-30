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
    Theme,
    NEXAStyles,
    ACCENT,
    Icon,
    SUCCESS,
    WARNING,
    get_font
)
from hub.i18n import tr

_PAGE_APPS = 0
_PAGE_HEALTH = 1
_PAGE_OPPORTUNITIES = 2


class AdminCenterView(QWidget):
    """Centro de administración de la plataforma."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_page = _PAGE_APPS
        self._plugins = []
        self._health_reports = {}
        self._opportunities = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._nav = QWidget()
        self._nav.setFixedWidth(200)
        self._nav.setStyleSheet(f"background-color: {Theme.surface()}; border-right: 1px solid {Theme.border()};")
        nav_layout = QVBoxLayout(self._nav)
        nav_layout.setContentsMargins(8, 16, 8, 16)
        nav_layout.setSpacing(4)

        self._title = QLabel("Admin Center")
        self._title.setFont(get_font(14, bold=True))
        self._title.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        nav_layout.addWidget(self._title)
        nav_layout.addSpacing(12)

        self._nav_buttons: list[QPushButton] = []
        nav_items = [
            ("Herramientas", _PAGE_APPS),
            ("Health Check", _PAGE_HEALTH),
            ("Oportunidades", _PAGE_OPPORTUNITIES),
        ]
        for label, page in nav_items:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, p=page, b=btn: self._navigate(p, b))
            nav_layout.addWidget(btn)
            self._nav_buttons.append(btn)
        nav_layout.addStretch()
        main_layout.addWidget(self._nav)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._create_apps_page())
        self._stack.addWidget(self._create_health_page())
        self._stack.addWidget(self._create_opportunities_page())
        main_layout.addWidget(self._stack, stretch=1)
        
        self._navigate(_PAGE_APPS, self._nav_buttons[0])

    def _create_apps_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self._header_apps = QLabel("Gestión de Herramientas")
        self._header_apps.setFont(get_font(18, bold=True))
        self._header_apps.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        layout.addWidget(self._header_apps)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(NEXAStyles.scroll_area())
        self._apps_content = QWidget()
        self._apps_content.setStyleSheet("background: transparent;")
        self._apps_grid = QGridLayout(self._apps_content)
        self._apps_grid.setSpacing(12)
        self._apps_grid.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self._apps_content)
        layout.addWidget(scroll, stretch=1)
        return page

    def _create_health_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self._header_health = QLabel("Health Check de Herramientas")
        self._header_health.setFont(get_font(18, bold=True))
        self._header_health.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        layout.addWidget(self._header_health)

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

        self._header_opp = QLabel("Búsquedas sin Resultado")
        self._header_opp.setFont(get_font(18, bold=True))
        self._header_opp.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        layout.addWidget(self._header_opp)

        self._subtitle_opp = QLabel("Estas búsquedas indican herramientas que los usuarios necesitan pero no existen.")
        self._subtitle_opp.setFont(get_font(12))
        self._subtitle_opp.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        layout.addWidget(self._subtitle_opp)

        self._opportunities_list = QVBoxLayout()
        self._opportunities_list.setSpacing(8)
        layout.addLayout(self._opportunities_list)
        layout.addStretch()
        return page

    def refresh_style(self) -> None:
        """Re-aplica el tema actual (claro/oscuro)."""
        self.setStyleSheet(f"QWidget {{ background-color: {Theme.bg()}; }}")
        self._nav.setStyleSheet(f"background-color: {Theme.surface()}; border-right: 1px solid {Theme.border()};")
        self._title.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        
        self._header_apps.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        self._header_health.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        self._header_opp.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        self._subtitle_opp.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        
        active_btn = self._nav_buttons[self._current_page]
        for idx, btn in enumerate(self._nav_buttons):
            if btn == active_btn:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {ACCENT};
                        color: #FFFFFF;
                        border: none;
                        border-radius: 6px;
                        padding: 10px 12px;
                        text-align: left;
                        font-size: 12px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {Theme.text()};
                        border: none;
                        border-radius: 6px;
                        padding: 10px 12px;
                        text-align: left;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{ background-color: {Theme.hover_bg()}; }}
                """)
                
        # Re-render content to apply updated card styles
        self.set_plugins(self._plugins)
        self.set_health_reports(self._health_reports)
        self.set_opportunities(self._opportunities)

    def _navigate(self, page: int, active_btn: QPushButton) -> None:
        self._current_page = page
        self._stack.setCurrentIndex(page)
        for btn in self._nav_buttons:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {Theme.text()};
                    border: none;
                    border-radius: 6px;
                    padding: 10px 12px;
                    text-align: left;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background-color: {Theme.hover_bg()}; }}
            """)
        active_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px 12px;
                text-align: left;
                font-size: 12px;
            }}
        """)

    def set_plugins(self, plugins: list[PluginDescriptor]) -> None:
        self._plugins = plugins
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
            name.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
            name_row.addWidget(name, stretch=1)
            status_color = SUCCESS if plugin.status.value == "oficial" else WARNING if plugin.status.value == "beta" else Theme.text_muted()
            status_lbl = QLabel(plugin.status.value.capitalize())
            status_lbl.setFont(get_font(10))
            status_lbl.setStyleSheet(f"color: {status_color}; background: transparent; border: none;")
            name_row.addWidget(status_lbl)
            card_layout.addLayout(name_row)

            meta = QLabel(f"v{plugin.version} · Owner: {plugin.owner} · {plugin.execution_count} ejecuciones")
            meta.setFont(get_font(10))
            meta.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
            card_layout.addWidget(meta)

            self._apps_grid.addWidget(card, i // 2, i % 2)

    def set_health_reports(self, reports: dict) -> None:
        self._health_reports = reports
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
            color = status_colors.get(report.status, Theme.text_muted())
            dot = QLabel("\u25cf")
            dot.setFont(get_font(18))
            dot.setStyleSheet(f"color: {color}; background: transparent; border: none;")
            card_layout.addWidget(dot)

            info = QVBoxLayout()
            info.setSpacing(2)
            name_lbl = QLabel(plugin_id)
            name_lbl.setFont(get_font(12, bold=True))
            name_lbl.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
            info.addWidget(name_lbl)
            msg_lbl = QLabel(report.message)
            msg_lbl.setFont(get_font(10))
            msg_lbl.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
            info.addWidget(msg_lbl)
            card_layout.addLayout(info, stretch=1)
            self._health_list.addWidget(card)

    def set_opportunities(self, opportunities: list[dict]) -> None:
        self._opportunities = opportunities
        while self._opportunities_list.count():
            item = self._opportunities_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not opportunities:
            empty = QLabel("No hay búsquedas sin resultado registradas.")
            empty.setFont(get_font(12))
            empty.setStyleSheet(f"color: {Theme.text_muted()}; padding: 20px; background: transparent; border: none;")
            self._opportunities_list.addWidget(empty)
            return

        for opp in opportunities:
            card = QFrame()
            card.setStyleSheet(NEXAStyles.card())
            card_layout = QHBoxLayout(card)

            query_icon = Icon("search", 15)
            query_icon.set_color(Theme.text_muted())
            card_layout.addWidget(query_icon)
            query_lbl = QLabel(f"\"{opp['query']}\"")
            query_lbl.setFont(get_font(12, bold=True))
            query_lbl.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
            card_layout.addWidget(query_lbl, stretch=1)

            count_lbl = QLabel(f"{opp['occurrences']} busqueda(s)")
            count_lbl.setFont(get_font(11))
            count_lbl.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
            card_layout.addWidget(count_lbl)

            self._opportunities_list.addWidget(card)
