"""UI — Enhanced Dashboard. Centro de control con KPIs, salud, favoritos y actividad."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from hub.i18n import tr
from hub.ui.common.design import (
    Theme,
    NEXAStyles,
    ACCENT,
    ERROR,
    INFO,
    Icon,
    SUCCESS,
    WARNING,
    AppCard,
    get_font,
)
from hub.models.plugin import PluginDescriptor


class KPICard(QFrame):
    def __init__(self, title: str, value: str = "0", icon: str = "",
                 color: str = ACCENT, parent=None):
        super().__init__(parent)
        self._color = color
        self._icon_name = icon
        self._title_text = title
        self.setObjectName("card")
        self._setup_layout(value)
        self.refresh_style()

    def _setup_layout(self, value: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(16, 14, 16, 14)
        top = QHBoxLayout()
        if self._icon_name:
            self._ico = Icon(self._icon_name, 20)
            self._ico.set_color(self._color)
            self._ico.setStyleSheet("background: transparent; border: none;")
            top.addWidget(self._ico)
        top.addStretch()
        layout.addLayout(top)
        self._value = QLabel(value)
        self._value.setFont(get_font(28, bold=True))
        self._value.setStyleSheet(f"color: {self._color}; background: transparent; border: none;")
        layout.addWidget(self._value)
        self._title = QLabel(self._title_text)
        self._title.setFont(get_font(11))
        self._title.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        layout.addWidget(self._title)

    def set_value(self, value: str) -> None:
        self._value.setText(value)

    def refresh_style(self) -> None:
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {Theme.card()};
                border: 1px solid {Theme.border()};
                border-left: 4px solid {self._color};
                border-radius: 12px;
            }}
        """)
        self._title.setStyleSheet(
            f"color: {Theme.text_secondary()}; background: transparent; border: none;")


class _SectionCard(QFrame):
    def __init__(self, title: str, icon: str = "", parent=None):
        super().__init__(parent)
        self._title_text = title
        self._icon_name = icon
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(18, 14, 18, 14)
        header = QHBoxLayout()
        if icon:
            ico = Icon(icon, 15)
            ico.set_color(ACCENT)
            ico.setStyleSheet("background: transparent; border: none;")
            header.addWidget(ico)
        self._header_lbl = QLabel(title)
        self._header_lbl.setFont(get_font(13, bold=True))
        self._header_lbl.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        header.addWidget(self._header_lbl)
        header.addStretch()
        layout.addLayout(header)
        self._body = QVBoxLayout()
        self._body.setSpacing(4)
        layout.addLayout(self._body)
        self._placeholder = QLabel(tr("dashboard.no_data"))
        self._placeholder.setFont(get_font(11, italic=True))
        self._placeholder.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        self._body.addWidget(self._placeholder)
        self.refresh_style()

    def clear_body(self) -> None:
        while self._body.count():
            item = self._body.takeAt(0)
            widget = item.widget()
            if widget:
                if widget == self._placeholder:
                    widget.setParent(None)
                else:
                    widget.deleteLater()

    def _set_placeholder(self, visible: bool = True) -> None:
        if visible:
            if self._placeholder.parent() is None:
                self._body.addWidget(self._placeholder)
            self._placeholder.setVisible(True)
        else:
            self._placeholder.setVisible(False)

    def refresh_style(self) -> None:
        self.setStyleSheet(
            f"QFrame#card {{ background-color: {Theme.card()};"
            f" border: 1px solid {Theme.border()}; border-radius: 12px; }}"
        )
        self._header_lbl.setStyleSheet(
            f"color: {Theme.text()}; background: transparent; border: none;")
        self._placeholder.setStyleSheet(
            f"color: {Theme.text_muted()}; background: transparent; border: none;")


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

        self._container = QWidget()
        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)
        scroll.setWidget(self._container)

        self._greeting = QLabel(f"{tr('dashboard.welcome')}, {self._user_name}")
        self._greeting.setFont(get_font(22, bold=True))
        self._greeting.setStyleSheet(f"color: {Theme.text()}; background: transparent;")
        layout.addWidget(self._greeting)

        self._subtitle = QLabel(tr("dashboard.subtitle"))
        self._subtitle.setFont(get_font(12))
        self._subtitle.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent;")
        layout.addWidget(self._subtitle)

        # Accesos directos a aplicaciones (clic abre el plugin)
        self._shortcuts_section = _SectionCard(tr("dashboard.shortcuts"), "zap")
        self._shortcuts_body = QHBoxLayout()
        self._shortcuts_body.setSpacing(14)
        self._shortcuts_section._body.addLayout(self._shortcuts_body)
        layout.addWidget(self._shortcuts_section)

        self._kpi_grid = QGridLayout()
        self._kpi_grid.setSpacing(14)
        self._kpis: dict[str, KPICard] = {}
        kpi_defs = [
            ("executions", tr("kpi.executions"), "trending-up", ACCENT),
            ("tools",      tr("kpi.tools"),      "grid",        INFO),
            ("users",      tr("kpi.users"),       "users",       SUCCESS),
            ("projects",   tr("kpi.projects"),    "folder",      "#9C27B0"),
            ("requests",   tr("kpi.requests"),    "file-text",   WARNING),
            ("articles",   tr("kpi.articles"),    "book-open",   "#00897B"),
            ("posts",      tr("kpi.posts"),       "users-round", "#5C6BC0"),
            ("incidents",  tr("kpi.incidents"),   "alert-circle",ERROR),
        ]
        for i, (key, title, icon, color) in enumerate(kpi_defs):
            card = KPICard(title, "0", icon, color)
            self._kpis[key] = card
            self._kpi_grid.addWidget(card, i // 4, i % 4)
        layout.addLayout(self._kpi_grid)

        self._pending_card = KPICard(tr("kpi.pending"), "0", "clock", WARNING)
        self._kpis["pending"] = self._pending_card
        self._kpi_grid.addWidget(self._pending_card, 2, 0)

        middle = QHBoxLayout()
        middle.setSpacing(16)

        self._favorites_section = _SectionCard(tr("dashboard.favorites"), "star")
        middle.addWidget(self._favorites_section, stretch=1)

        self._health_section = _SectionCard(tr("dashboard.pending_requests"), "alert-triangle")
        middle.addWidget(self._health_section, stretch=1)

        layout.addLayout(middle)

        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        self._activity_section = _SectionCard(tr("dashboard.recent_activity"), "activity")
        bottom.addWidget(self._activity_section, stretch=1)

        self._tools_section = _SectionCard(tr("dashboard.recent_tools"), "clock")
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
            icon = QLabel(item.get("icon", "●"))
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

    def set_shortcuts(self, plugins: list[PluginDescriptor]) -> None:
        """Renderiza tarjetas de aplicaciones destacadas, clicables, en la
        pantalla de inicio (accesos directos)."""
        while self._shortcuts_body.count():
            item = self._shortcuts_body.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        if not plugins:
            self._shortcuts_section.clear_body()
            self._shortcuts_section._set_placeholder(True)
            return
        self._shortcuts_section.clear_body()
        self._shortcuts_section._set_placeholder(False)
        for p in plugins[:4]:
            card = AppCard(
                plugin_id=p.id,
                name=p.name,
                description=p.description,
                category=p.category.value,
                status=getattr(p, "status", "oficial").value
                if hasattr(getattr(p, "status", "oficial"), "value") else "oficial",
                execution_count=getattr(p, "execution_count", 0),
                is_favorite=False,
                icon_name=p.icon or "package",
                on_click=lambda pid: self.plugin_clicked.emit(pid),
            )
            card.setFixedWidth(260)
            card._fav_btn.hide()
            self._shortcuts_body.addWidget(card)
        self._shortcuts_body.addStretch()

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
            label = tr("kpi.executions_count").format(n=tool.get("executions", 0))
            count = QLabel(label)
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
        active   = stats.get("active", 0)
        paused   = stats.get("paused", 0)
        problems = stats.get("problems", 0)
        total    = active + paused + problems
        indicators = [
            ("●", SUCCESS, tr("health.active").format(n=active)),
            ("●", WARNING, tr("health.paused").format(n=paused)),
            ("●", ERROR,   tr("health.problems").format(n=problems)),
            ("●", Theme.text_muted(), tr("health.total").format(n=total)),
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

    def refresh_style(self) -> None:
        """Llamado por apply_theme() para respetar el modo activo."""
        self._container.setStyleSheet(
            f"QWidget {{ background-color: {Theme.bg()}; }}")
        self._greeting.setStyleSheet(f"color: {Theme.text()}; background: transparent;")
        self._subtitle.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent;")
        for card in self._kpis.values():
            card.refresh_style()
        for sec in (self._favorites_section, self._health_section,
                    self._activity_section, self._tools_section,
                    self._shortcuts_section):
            sec.refresh_style()
