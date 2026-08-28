"""UI — Enhanced Dashboard. Centro de control con KPIs, salud, favoritos y actividad."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from hub.ui.common.design import (
    Theme,
    NEXAStyles,
    ACCENT,
    ERROR,
    INFO,
    Icon,
    SUCCESS,
    WARNING,
    get_font
)


class KPICard(QFrame):
    def __init__(self, title: str, value: str = "0", icon: str = "",
                 color: str = ACCENT, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {Theme.surface()};
                border: 1px solid {Theme.border()};
                border-left: 4px solid {color};
                border-radius: 10px;
                padding: 16px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        top = QHBoxLayout()
        if icon:
            ico = Icon(icon, 20)
            ico.set_color(color)
            ico.setStyleSheet("background: transparent; border: none;")
            top.addWidget(ico)
        top.addStretch()
        layout.addLayout(top)
        self._value = QLabel(value)
        self._value.setFont(get_font(28, bold=True))
        self._value.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        layout.addWidget(self._value)
        self._title = QLabel(title)
        self._title.setFont(get_font(11))
        self._title.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        layout.addWidget(self._title)

    def set_value(self, value: str) -> None:
        self._value.setText(value)


class _SectionCard(QFrame):
    def __init__(self, title: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(NEXAStyles.card_no_hover())
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(18, 14, 18, 14)
        header = QHBoxLayout()
        if icon:
            ico = Icon(icon, 15)
            ico.set_color(ACCENT)
            ico.setStyleSheet("background: transparent; border: none;")
            header.addWidget(ico)
        lbl = QLabel(title)
        lbl.setFont(get_font(13, bold=True))
        lbl.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        header.addWidget(lbl)
        header.addStretch()
        layout.addLayout(header)
        self._body = QVBoxLayout()
        self._body.setSpacing(4)
        layout.addLayout(self._body)
        self._placeholder = QLabel("Sin datos disponibles")
        self._placeholder.setFont(get_font(11, italic=True))
        self._placeholder.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        self._body.addWidget(self._placeholder)

    def clear_body(self) -> None:
        while self._body.count():
            item = self._body.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _set_placeholder(self, visible: bool = True) -> None:
        if visible:
            if self._placeholder.parent() is None:
                self._body.addWidget(self._placeholder)
            self._placeholder.setVisible(True)
        else:
            self._placeholder.setVisible(False)


class EnhancedDashboardView(QWidget):
    """Dashboard mejorado con KPIs, salud de apps, favoritos, actividad y solicitudes."""

    plugin_clicked = Signal(str)

    def __init__(self, user_name: str = "Usuario", parent=None) -> None:
        super().__init__(parent)
        self._user_name = user_name
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(NEXAStyles.scroll_area())
        outer.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        scroll.setWidget(container)

        greeting = QLabel(f"Bienvenido, {self._user_name}")
        greeting.setFont(get_font(20, bold=True))
        greeting.setStyleSheet(f"color: {Theme.text()}; background: transparent;")
        layout.addWidget(greeting)

        subtitle = QLabel("Resumen de la plataforma NEXA Productivity Hub")
        subtitle.setFont(get_font(12))
        subtitle.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent;")
        layout.addWidget(subtitle)

        self._kpi_grid = QGridLayout()
        self._kpi_grid.setSpacing(12)
        self._kpis: dict[str, KPICard] = {}
        kpi_defs = [
            ("executions", "Ejecuciones", "play", ACCENT),
            ("tools", "Herramientas", "apps", INFO),
            ("users", "Usuarios", "users", SUCCESS),
            ("projects", "Proyectos", "folder", "#9C27B0"),
            ("requests", "Solicitudes", "list", WARNING),
            ("articles", "Conocimiento", "book", "#00897B"),
            ("posts", "Publicaciones", "activity", "#5C6BC0"),
            ("incidents", "Incidentes", "flag", ERROR),
        ]
        for i, (key, title, icon, color) in enumerate(kpi_defs):
            card = KPICard(title, "0", icon, color)
            self._kpis[key] = card
            self._kpi_grid.addWidget(card, i // 4, i % 4)
        layout.addLayout(self._kpi_grid)

        self._pending_card = KPICard("Pendientes", "0", "clock", WARNING)
        self._kpis["pending"] = self._pending_card  # registrar para update_kpi()
        self._kpi_grid.addWidget(self._pending_card, 2, 0)

        middle = QHBoxLayout()
        middle.setSpacing(16)

        self._favorites_section = _SectionCard("Mis aplicaciones favoritas", "star")
        middle.addWidget(self._favorites_section, stretch=1)

        self._health_section = _SectionCard("Solicitudes e Incidencias pendientes", "alert-triangle")
        middle.addWidget(self._health_section, stretch=1)

        layout.addLayout(middle)

        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        self._activity_section = _SectionCard("Actualizaciones y Mejoras recientes", "activity")
        bottom.addWidget(self._activity_section, stretch=1)

        self._tools_section = _SectionCard("Aplicaciones recientemente utilizadas", "clock")
        bottom.addWidget(self._tools_section, stretch=1)

        layout.addLayout(bottom, stretch=1)

    def update_kpi(self, key: str, value: str) -> None:
        if key in self._kpis:
            self._kpis[key].set_value(value)

    def set_activity(self, items: list[dict]) -> None:
        self._activity_section.clear_body()
        if not items:
            self._activity_section._set_placeholder(True)
            return
        self._activity_section._set_placeholder(False)
        for item in items[:8]:
            row = QHBoxLayout()
            icon = QLabel(item.get("icon", "\u25cf"))
            icon.setFont(get_font(12))
            icon.setStyleSheet(f"color: {item.get('color', ACCENT)}; background: transparent; border: none;")
            row.addWidget(icon)
            text = QLabel(item.get("text", ""))
            text.setFont(get_font(11))
            text.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
            row.addWidget(text, stretch=1)
            time_lbl = QLabel(item.get("time", ""))
            time_lbl.setFont(get_font(9))
            time_lbl.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
            row.addWidget(time_lbl)
            c = QWidget()
            c.setLayout(row)
            self._activity_section._body.addWidget(c)

    def set_popular_tools(self, tools: list[dict]) -> None:
        self._tools_section.clear_body()
        if not tools:
            self._tools_section._set_placeholder(True)
            return
        self._tools_section._set_placeholder(False)
        for tool in tools[:6]:
            row = QHBoxLayout()
            name = QLabel(tool.get("name", ""))
            name.setFont(get_font(11, bold=True))
            name.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
            row.addWidget(name, stretch=1)
            count = QLabel(f"{tool.get('executions', 0)} ejecuciones")
            count.setFont(get_font(10))
            count.setStyleSheet(f"color: {ACCENT}; background: transparent; border: none;")
            row.addWidget(count)
            c = QWidget()
            c.setLayout(row)
            self._tools_section._body.addWidget(c)

    def set_favorites(self, tools: list[dict]) -> None:
        self._favorites_section.clear_body()
        if not tools:
            self._favorites_section._set_placeholder(True)
            return
        self._favorites_section._set_placeholder(False)
        for tool in tools[:6]:
            row = QHBoxLayout()
            ico = Icon("star", 13)
            ico.set_color(ACCENT)
            ico.setStyleSheet("background: transparent; border: none;")
            row.addWidget(ico)
            name = QLabel(tool.get("name", ""))
            name.setFont(get_font(11, bold=True))
            name.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
            row.addWidget(name, stretch=1)
            cat = QLabel(tool.get("category", ""))
            cat.setFont(get_font(9))
            cat.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
            row.addWidget(cat)
            c = QWidget()
            c.setLayout(row)
            self._favorites_section._body.addWidget(c)

    def set_app_health(self, stats: dict) -> None:
        self._health_section.clear_body()
        if not stats:
            self._health_section._set_placeholder(True)
            return
        self._health_section._set_placeholder(False)
        active = stats.get("active", 0)
        paused = stats.get("paused", 0)
        problems = stats.get("problems", 0)
        total = active + paused + problems
        indicators = [
            ("\u25cf", SUCCESS, f"{active} activas"),
            ("\u25cf", WARNING, f"{paused} en pausa"),
            ("\u25cf", ERROR, f"{problems} con problemas"),
            ("\u25cf", Theme.text_muted(), f"{total} en total"),
        ]
        for icon_char, color, text in indicators:
            row = QHBoxLayout()
            ic = QLabel(icon_char)
            ic.setFont(get_font(12))
            ic.setStyleSheet(f"color: {color}; background: transparent; border: none;")
            row.addWidget(ic)
            lbl = QLabel(text)
            lbl.setFont(get_font(11))
            lbl.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
            row.addWidget(lbl, stretch=1)
            c = QWidget()
            c.setLayout(row)
            self._health_section._body.addWidget(c)

    def set_pending_requests(self, count: int) -> None:
        self._pending_card.set_value(str(count))
