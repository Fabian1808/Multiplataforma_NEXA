"""UI — App Viewer. Pantalla de aplicación: hero, KPIs, archivos, configuración,
ejecución, historial reciente y área del plugin embebido."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QStackedWidget,
    QGridLayout,
    QSizePolicy,
)

from hub.core.plugin_registry import PluginRegistry
from hub.models.plugin import PluginDescriptor
from hub.ui.common.design import (
    NEXAStyles,
    Theme,
    ACCENT,
    Icon,
    StatusBadge,
    KPIWidget,
    get_font,
    is_dark,
)

logger = logging.getLogger(__name__)


class AppViewer(QWidget):
    """Pantalla de aplicación re-diseñada (hero + cards + plugin)."""

    back_clicked = Signal()
    favorite_toggled = Signal(str, bool)

    def __init__(self, registry: PluginRegistry, launcher=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._registry = registry
        self._launcher = launcher
        self._current_plugin: PluginDescriptor | None = None
        self._is_favorite = False
        self._exec_count = 0
        self._setup_ui()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        from PySide6.QtWidgets import QScrollArea

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(NEXAStyles.scroll_area())
        body = QWidget()
        body.setObjectName("appBody")
        body.setStyleSheet(f"QWidget#appBody {{ background-color: {Theme.bg()}; }}")
        v = QVBoxLayout(body)
        v.setContentsMargins(28, 24, 28, 28)
        v.setSpacing(22)

        # ---------- Barra superior ----------
        v.addLayout(self._build_top_bar())

        # ---------- Hero ----------
        v.addWidget(self._build_hero())

        # ---------- Contenido: plugin + archivos + recientes ----------
        content = QHBoxLayout()
        content.setSpacing(20)

        left = QVBoxLayout()
        left.setSpacing(20)
        left.addWidget(self._build_plugin_card())
        left.addWidget(self._build_files_card())
        content.addLayout(left, stretch=3)

        right = QVBoxLayout()
        right.setSpacing(20)
        right.addWidget(self._build_config_card())
        right.addWidget(self._build_recent_card())
        content.addLayout(right, stretch=2)

        v.addLayout(content)
        v.addStretch()

        scroll.setWidget(body)
        outer.addWidget(scroll)

        self._content_stack = QStackedWidget()
        # (mantenemos la pila interna para error / estado)
        self._build_content_stack()
        self._content_stack.hide()

    # ------------------------------------------------------------------
    def _build_top_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        self._back_btn = QPushButton()
        back_icon = Icon("back", 15)
        back_icon.set_color(Theme.text_secondary())
        self._back_btn.setLayout(QVBoxLayout())
        self._back_btn.layout().setContentsMargins(0, 0, 0, 0)
        self._back_btn.layout().addWidget(back_icon, 0, Qt.AlignmentFlag.AlignCenter)
        self._back_btn.setFixedSize(36, 36)
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.setStyleSheet(
            f"QPushButton {{ background-color: {Theme.hover_bg()}; border: 1px solid {Theme.border()}; "
            f"border-radius: 10px; }}"
            f"QPushButton:hover {{ border-color: {ACCENT}; }}")
        self._back_btn.clicked.connect(lambda: self.back_clicked.emit())
        row.addWidget(self._back_btn)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        self._title = QLabel("Aplicación")
        self._title.setFont(get_font(20, weight=700))
        self._title.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        title_col.addWidget(self._title)
        self._description = QLabel("")
        self._description.setFont(get_font(12))
        self._description.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        self._description.setWordWrap(True)
        title_col.addWidget(self._description)
        row.addLayout(title_col, stretch=1)

        row.addStretch()
        row.addLayout(self._build_tag_row())
        return row

    def _build_tag_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        self._status_badge = StatusBadge("desconocido")
        row.addWidget(self._status_badge)
        self._version_label = QLabel("")
        self._version_label.setFont(get_font(11))
        self._version_label.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        row.addWidget(self._version_label)
        return row

    def _build_hero(self) -> QFrame:
        hero = QFrame()
        hero.setObjectName("card")
        hero.setStyleSheet(NEXAStyles.card_no_hover())
        grid = QGridLayout(hero)
        grid.setContentsMargins(24, 22, 24, 22)
        grid.setSpacing(16)

        # KPI cards
        self._kpi_status = KPIWidget("Estado", "—", "flag", ACCENT)
        self._kpi_last = KPIWidget("Última ejecución", "—", "clock", Theme.text_secondary())
        self._kpi_count = KPIWidget("Ejecuciones", "0", "play", ACCENT)
        grid.addWidget(self._kpi_status, 0, 0)
        grid.addWidget(self._kpi_last, 0, 1)
        grid.addWidget(self._kpi_count, 0, 2)
        return hero

    def _build_plugin_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(NEXAStyles.card())
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 18)
        v.setSpacing(12)

        head = QHBoxLayout()
        ico = Icon("plugin", 18)
        ico.set_color(ACCENT)
        head.addWidget(ico)
        title = QLabel("Espacio de trabajo")
        title.setFont(get_font(13, weight=600))
        title.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        head.addWidget(title)
        head.addStretch()
        v.addLayout(head)

        self._plugin_container = QWidget()
        self._plugin_layout = QVBoxLayout(self._plugin_container)
        self._plugin_layout.setContentsMargins(0, 0, 0, 0)
        self._plugin_layout.setSpacing(10)
        self._placeholder = self._empty_state()
        self._plugin_layout.addWidget(self._placeholder, stretch=1)
        v.addWidget(self._plugin_container, stretch=1)
        return card

    def _empty_state(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 30, 20, 30)
        lay.setSpacing(10)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico = Icon("apps", 34)
        ico.set_color(Theme.text_muted())
        lay.addWidget(ico, 0, Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel("La interfaz del plugin se cargará aquí")
        lbl.setFont(get_font(13))
        lbl.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)
        hint = QLabel("Pulsa Ejecutar para lanzar esta herramienta")
        hint.setFont(get_font(11))
        hint.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)
        return w

    def _build_files_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(NEXAStyles.card())
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 18)
        v.setSpacing(10)

        head = QHBoxLayout()
        ico = Icon("folder", 18)
        ico.set_color(ACCENT)
        head.addWidget(ico)
        title = QLabel("Archivos de entrada")
        title.setFont(get_font(13, weight=600))
        title.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        head.addWidget(title)
        head.addStretch()
        v.addLayout(head)

        drop = QFrame()
        drop.setStyleSheet(
            f"QFrame {{ border: 1.5px dashed {Theme.border_strong()}; border-radius: 12px; "
            f"background-color: {Theme.input_bg()}; }}")
        dl = QVBoxLayout(drop)
        dl.setContentsMargins(16, 22, 16, 22)
        dl.setSpacing(6)
        dl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        up_ico = Icon("upload", 22)
        up_ico.set_color(Theme.text_secondary())
        dl.addWidget(up_ico, 0, Qt.AlignmentFlag.AlignCenter)
        t1 = QLabel("Arrastra archivos aquí o")
        t1.setFont(get_font(12))
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t1.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        dl.addWidget(t1)
        browse = QPushButton("Seleccionar archivos")
        browse.setStyleSheet(NEXAStyles.secondary_button())
        browse.setCursor(Qt.CursorShape.PointingHandCursor)
        dl.addWidget(browse, 0, Qt.AlignmentFlag.AlignCenter)
        v.addWidget(drop)

        self._file_list = QFrame()
        self._file_list.setStyleSheet("background: transparent; border: none;")
        self._file_layout = QVBoxLayout(self._file_list)
        self._file_layout.setContentsMargins(0, 0, 0, 0)
        self._file_layout.setSpacing(6)
        v.addWidget(self._file_list)
        return card

    def _build_config_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(NEXAStyles.card())
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 18)
        v.setSpacing(10)

        head = QHBoxLayout()
        ico = Icon("settings", 18)
        ico.set_color(ACCENT)
        head.addWidget(ico)
        title = QLabel("Configuración")
        title.setFont(get_font(13, weight=600))
        title.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        head.addWidget(title)
        head.addStretch()
        v.addLayout(head)

        self._execute_btn = QPushButton()
        ex_icon = Icon("play", 15)
        ex_icon.set_color("#FFFFFF")
        self._execute_btn.setLayout(QHBoxLayout())
        self._execute_btn.layout().setContentsMargins(16, 0, 16, 0)
        self._execute_btn.layout().setSpacing(8)
        self._execute_btn.layout().addWidget(ex_icon, 0, Qt.AlignmentFlag.AlignCenter)
        ex_text = QLabel("Ejecutar")
        ex_text.setFont(get_font(13, weight=600))
        ex_text.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        self._execute_btn.layout().addWidget(ex_text, 0, Qt.AlignmentFlag.AlignCenter)
        self._execute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._execute_btn.setFixedHeight(44)
        self._execute_btn.setStyleSheet(NEXAStyles.primary_button())
        self._execute_btn.clicked.connect(self._on_execute)
        v.addWidget(self._execute_btn)

        self._fav_btn = QPushButton("  Añadir a favoritos")
        self._fav_btn.setStyleSheet(NEXAStyles.secondary_button())
        self._fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fav_btn.setFixedHeight(40)
        self._fav_btn.clicked.connect(self._toggle_favorite)
        v.addWidget(self._fav_btn)

        self._owner_label = QLabel("")
        self._owner_label.setFont(get_font(11))
        self._owner_label.setWordWrap(True)
        self._owner_label.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        v.addWidget(self._owner_label)
        return card

    def _build_recent_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(NEXAStyles.card())
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 18)
        v.setSpacing(10)

        head = QHBoxLayout()
        ico = Icon("clock", 18)
        ico.set_color(ACCENT)
        head.addWidget(ico)
        title = QLabel("Últimas ejecuciones")
        title.setFont(get_font(13, weight=600))
        title.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        head.addWidget(title)
        head.addStretch()
        v.addLayout(head)

        self._recent_container = QFrame()
        self._recent_container.setStyleSheet("background: transparent; border: none;")
        self._recent_layout = QVBoxLayout(self._recent_container)
        self._recent_layout.setContentsMargins(0, 0, 0, 0)
        self._recent_layout.setSpacing(6)
        empty = QLabel("Sin ejecuciones todavía")
        empty.setFont(get_font(12))
        empty.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._recent_layout.addWidget(empty)
        v.addWidget(self._recent_container)
        return card

    def _build_content_stack(self) -> None:
        error = QWidget()
        el = QVBoxLayout(error)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel("No se pudo cargar esta aplicación")
        label.setFont(get_font(16, weight=600))
        label.setStyleSheet(f"color: #E5484D; background: transparent; border: none;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(label)
        self._error_detail = QLabel("")
        self._error_detail.setFont(get_font(11))
        self._error_detail.setStyleSheet(f"color: {Theme.text_secondary()};")
        self._error_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_detail.setWordWrap(True)
        el.addWidget(self._error_detail)
        retry_btn = QPushButton("Reintentar")
        retry_btn.setStyleSheet(NEXAStyles.primary_button())
        retry_btn.setFixedWidth(140)
        retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        retry_btn.clicked.connect(self._retry_load)
        el.addWidget(retry_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self._content_stack.addWidget(error)

    # ------------------------------------------------------------------
    def refresh_style(self) -> None:
        """Reconstruye la página con el tema activo (claro/oscuro)."""
        # Reconstruye el body con los colores actuales de Theme.
        while self.layout() and self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._setup_ui()
        if self._current_plugin:
            self.load_plugin(self._current_plugin.id)

    def load_plugin(self, plugin_id: str) -> None:
        desc = self._registry.get(plugin_id)
        if not desc:
            self._show_error(f"Plugin no encontrado: {plugin_id}")
            return

        self._current_plugin = desc
        self._title.setText(desc.name)
        self._description.setText(desc.description or "")
        self._version_label.setText(f"v{desc.version}")
        self._owner_label.setText(f"Owner: {desc.owner}")
        self._kpi_status.set_value(desc.status.value.capitalize())

        status_icon = {"activo": "#2E9E5B", "oficial": "green", "experimental": "amber"}.get(
            desc.status.value, ACCENT)
        from hub.ui.common.design import PLUGIN_STATUS_BADGES
        label, color = PLUGIN_STATUS_BADGES.get(desc.status.value, (desc.status.value, Theme.text_muted()))
        self._status_badge.setText(label)
        self._status_badge.setStyleSheet(NEXAStyles.badge(label, color))

        self._load_recent(desc)

        try:
            self._load_plugin_widget(desc)
        except Exception as e:
            logger.exception("Error cargando widget del plugin %s", plugin_id)
            self._show_error(str(e))

    def _load_recent(self, desc: PluginDescriptor) -> None:
        while self._recent_layout.count():
            item = self._recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # Datos de demostración encadenados a la app cargada
        samples = [
            (f"{desc.name} — lote de prueba", "hace 2 h", True),
            ("Validación de datos", "ayer", True),
            ("Exportación de resultados", "hace 3 días", False),
        ]
        for name, ts, ok in samples:
            self._recent_layout.addWidget(self._recent_row(name, ts, ok))

    def _recent_row(self, name: str, ts: str, ok: bool) -> QWidget:
        row = QFrame()
        row.setStyleSheet(f"QFrame {{ background-color: {Theme.hover_bg()}; border-radius: 8px; }}")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)
        dot = QFrame()
        dot.setFixedSize(8, 8)
        color = "#2E9E5B" if ok else "#E5484D"
        dot.setStyleSheet(f"background-color: {color}; border-radius: 4px; border: none;")
        lay.addWidget(dot)
        t = QLabel(name)
        t.setFont(get_font(11))
        t.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        lay.addWidget(t, stretch=1)
        ts_lbl = QLabel(ts)
        ts_lbl.setFont(get_font(10))
        ts_lbl.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        lay.addWidget(ts_lbl)
        return row

    def _load_plugin_widget(self, desc: PluginDescriptor) -> None:
        while self._plugin_layout.count():
            item = self._plugin_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Herramientas externas: mostrar la tarjeta de "abrir aplicación" en vez
        # de incrustar un widget (evita congelar el hub y mantiene el binario aislado).
        if desc.is_external:
            self._plugin_layout.addWidget(self._external_panel(desc), stretch=1)
            return

        factory = self._registry.get_factory(desc.id)
        if factory:
            widget = factory.create_widget(self._plugin_container)
            self._plugin_layout.addWidget(widget)
            return

        try:
            module = self._registry.load_plugin_module(desc.id)
            if hasattr(module, "create_widget"):
                widget = module.create_widget(self._plugin_container)
                self._plugin_layout.addWidget(widget)
            else:
                info = QLabel(f"Módulo cargado: {desc.entrypoint}\nNo se encontró create_widget()")
                info.setFont(get_font(12))
                info.setStyleSheet(f"color: {Theme.text_secondary()}; padding: 20px;")
                info.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._plugin_layout.addWidget(info)
        except Exception as e:
            info = QLabel(f"No se pudo cargar el módulo: {e}")
            info.setFont(get_font(12))
            info.setStyleSheet("color: #E5484D; padding: 20px;")
            info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._plugin_layout.addWidget(info)

    def _external_panel(self, desc: PluginDescriptor) -> QWidget:
        """Panel para herramientas externas: estado de instalación + abrir."""
        from PySide6.QtWidgets import QMessageBox

        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(14)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        outer_ico = Icon("cube", 44)
        outer_ico.set_color(ACCENT)
        lay.addWidget(outer_ico, 0, Qt.AlignmentFlag.AlignCenter)

        type_lbl = QLabel("Aplicación de escritorio independiente")
        type_lbl.setFont(get_font(13, weight=600))
        type_lbl.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        type_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(type_lbl)

        installed = bool(self._launcher and self._launcher.is_installed(desc))
        state = "Instalada — lista para abrir" if installed else "No instalada — se descargará al abrir"
        state_lbl = QLabel(state)
        state_lbl.setFont(get_font(11))
        state_lbl.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        state_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(state_lbl)

        hint = QLabel(
            "Esta herramienta se ejecuta por separado del Hub.\n"
            "Al pulsar 'Abrir aplicación' se inicia como proceso independiente.")
        hint.setFont(get_font(11))
        hint.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        lay.addWidget(hint)

        open_btn = QPushButton("  Abrir aplicación")
        open_btn.setStyleSheet(NEXAStyles.primary_button())
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setFixedWidth(220)
        open_btn.setFixedHeight(44)
        icon = Icon("play", 15)
        icon.set_color("#FFFFFF")
        open_btn.setLayout(QHBoxLayout())
        open_btn.layout().setContentsMargins(16, 0, 16, 0)
        open_btn.layout().setSpacing(8)
        open_btn.layout().addWidget(icon, 0, Qt.AlignmentFlag.AlignCenter)
        open_txt = QLabel("Abrir aplicación")
        open_txt.setFont(get_font(13, weight=600))
        open_txt.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        open_btn.layout().addWidget(open_txt, 0, Qt.AlignmentFlag.AlignCenter)
        open_btn.clicked.connect(lambda: self._launch_external(desc))
        lay.addWidget(open_btn, 0, Qt.AlignmentFlag.AlignCenter)

        return w

    def _launch_external(self, desc: PluginDescriptor) -> None:
        from PySide6.QtWidgets import QMessageBox
        if self._launcher is None:
            QMessageBox.warning(self, "No disponible", "El lanzador de aplicaciones no está configurado.")
            return
        ok, msg = self._launcher.launch(desc)
        if ok:
            self._exec_count += 1
            self._kpi_count.set_value(str(self._exec_count))
            QMessageBox.information(self, "Abrir aplicación", msg)
        else:
            QMessageBox.warning(self, "No se pudo abrir", msg)

    def _show_error(self, message: str) -> None:
        self._error_detail.setText(message)
        self._content_stack.setCurrentIndex(0)
        self._content_stack.show()

    def _retry_load(self) -> None:
        if self._current_plugin:
            self.load_plugin(self._current_plugin.id)

    def _toggle_favorite(self) -> None:
        if self._current_plugin:
            self._is_favorite = not self._is_favorite
            self._fav_btn.setText(
                "  Quitar de favoritos" if self._is_favorite else "  Añadir a favoritos")
            self.favorite_toggled.emit(self._current_plugin.id, self._is_favorite)

    def _on_execute(self) -> None:
        if self._current_plugin:
            logger.info("Ejecutando plugin: %s", self._current_plugin.id)
            self._execute_btn.setEnabled(False)
            try:
                factory = self._registry.get_factory(self._current_plugin.id)
                if factory:
                    widget = factory.create_widget(self._plugin_container)
                    self._plugin_layout.addWidget(widget)
                    self._exec_count += 1
                    self._kpi_count.set_value(str(self._exec_count))
            except Exception as e:
                logger.exception("Error ejecutando plugin %s", self._current_plugin.id)
                self._show_error(str(e))
            self._execute_btn.setEnabled(True)
