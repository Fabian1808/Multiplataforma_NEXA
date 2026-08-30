"""UI — Catalog View. Catálogo completo de aplicaciones con diseño de App Store."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QPushButton,
)

from hub.i18n import tr
from hub.models.plugin import PluginCategory, PluginDescriptor
from hub.ui.common.design import (
    Theme,
    NEXAStyles,
    ACCENT,
    AppCard,
    Icon,
    get_font
)


class AppCarousel(QWidget):
    """Barra horizontal scrollable de aplicaciones."""

    card_clicked = Signal(str)
    fav_toggled = Signal(str, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._plugins: list[PluginDescriptor] = []
        self._fav_ids: list[str] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFixedHeight(230)
        self._scroll.setStyleSheet(NEXAStyles.scroll_area())

        self._row_widget = QWidget()
        self._row_layout = QHBoxLayout(self._row_widget)
        self._row_layout.setContentsMargins(4, 4, 4, 4)
        self._row_layout.setSpacing(16)
        self._scroll.setWidget(self._row_widget)
        layout.addWidget(self._scroll)

    def set_items(self, plugins: list[PluginDescriptor], fav_ids: list[str]) -> None:
        self._plugins = plugins
        self._fav_ids = fav_ids
        self._render()

    def _render(self) -> None:
        while self._row_layout.count():
            item = self._row_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for plugin in self._plugins:
            is_fav = plugin.id in self._fav_ids
            card = AppCard(
                plugin_id=plugin.id,
                name=plugin.name,
                description=plugin.description,
                category=plugin.category.value,
                execution_count=plugin.execution_count,
                is_favorite=is_fav,
                icon_name=plugin.icon or "package",
                logo_path=plugin.logo,
                on_click=lambda pid: self.card_clicked.emit(pid),
            )
            card.setFixedWidth(280)
            card._fav_btn.clicked.connect(
                lambda _, pid=plugin.id, fav=is_fav: self.fav_toggled.emit(pid, not fav)
            )
            self._row_layout.addWidget(card)

        self._row_layout.addStretch()


class CatalogView(QWidget):
    """Catálogo de aplicaciones con diseño de tienda (App Store)."""

    plugin_clicked = Signal(str)
    favorite_toggled = Signal(str, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._all_plugins: list[PluginDescriptor] = []
        self._favorite_ids: list[str] = []
        self._current_category: PluginCategory | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"QWidget {{ background-color: {Theme.bg()}; }}")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 28)
        main_layout.setSpacing(18)

        # Header
        title_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self._header = QLabel("NEXA Store")
        self._header.setFont(get_font(24, weight=800))
        self._header.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        title_col.addWidget(self._header)
        self._count_label = QLabel("")
        self._count_label.setFont(get_font(12))
        self._count_label.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        title_col.addWidget(self._count_label)
        title_row.addLayout(title_col)
        title_row.addStretch()
        main_layout.addLayout(title_row)

        # Categories
        self._categories_bar = QScrollArea()
        self._categories_bar.setWidgetResizable(True)
        self._categories_bar.setFixedHeight(44)
        self._categories_bar.setFrameShape(QFrame.Shape.NoFrame)
        self._categories_bar.setStyleSheet(NEXAStyles.scroll_area())
        self._categories_bar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._categories_bar.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._cat_container = QWidget()
        self._cat_layout = QHBoxLayout(self._cat_container)
        self._cat_layout.setContentsMargins(0, 0, 0, 0)
        self._cat_layout.setSpacing(8)
        self._categories_bar.setWidget(self._cat_container)
        main_layout.addWidget(self._categories_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(NEXAStyles.scroll_area())
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(24)

        # Hero Banner
        self._hero_frame = QFrame()
        self._hero_frame.setStyleSheet(f"background-color: {ACCENT}15; border-radius: 16px;")
        hero_layout = QHBoxLayout(self._hero_frame)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        
        hero_info = QVBoxLayout()
        self._hero_badge = QLabel("DESTACADO")
        self._hero_badge.setFont(get_font(10, bold=True))
        self._hero_badge.setStyleSheet(f"color: {ACCENT}; background: transparent; border: none;")
        hero_info.addWidget(self._hero_badge)
        
        self._hero_title = QLabel("Cargando...")
        self._hero_title.setFont(get_font(22, bold=True))
        self._hero_title.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        hero_info.addWidget(self._hero_title)
        
        self._hero_desc = QLabel("")
        self._hero_desc.setFont(get_font(12))
        self._hero_desc.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        self._hero_desc.setWordWrap(True)
        hero_info.addWidget(self._hero_desc)
        
        hero_info.addSpacing(12)
        self._hero_btn = QPushButton("Abrir Aplicación")
        self._hero_btn.setFont(get_font(12, bold=True))
        self._hero_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                color: #FFFFFF;
                border: none;
                border-radius: 20px;
                padding: 10px 24px;
            }}
            QPushButton:hover {{
                background-color: #E64A00;
            }}
        """)
        self._hero_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hero_btn.setFixedWidth(200)
        hero_info.addWidget(self._hero_btn)
        hero_layout.addLayout(hero_info, stretch=1)
        
        hero_icon_lbl = Icon("award", 80)
        hero_icon_lbl.set_color(ACCENT)
        hero_layout.addWidget(hero_icon_lbl)
        
        self._content_layout.addWidget(self._hero_frame)

        # Favorites Carousel
        self._fav_section = QWidget()
        self._fav_section_layout = QVBoxLayout(self._fav_section)
        self._fav_section_layout.setContentsMargins(0, 0, 0, 0)
        self._fav_section_layout.setSpacing(10)
        self._fav_head = self._section_head("star", "Mis Favoritos", ACCENT)
        self._fav_section_layout.addLayout(self._fav_head)
        self._fav_carousel = AppCarousel()
        self._fav_carousel.card_clicked.connect(self._on_card_clicked)
        self._fav_carousel.fav_toggled.connect(self._on_fav_toggled)
        self._fav_section_layout.addWidget(self._fav_carousel)
        self._content_layout.addWidget(self._fav_section)

        # Popular Carousel
        self._pop_section = QWidget()
        self._pop_section_layout = QVBoxLayout(self._pop_section)
        self._pop_section_layout.setContentsMargins(0, 0, 0, 0)
        self._pop_section_layout.setSpacing(10)
        self._pop_head = self._section_head("trending-up", "Más Populares", Theme.text())
        self._pop_section_layout.addLayout(self._pop_head)
        self._pop_carousel = AppCarousel()
        self._pop_carousel.card_clicked.connect(self._on_card_clicked)
        self._pop_carousel.fav_toggled.connect(self._on_fav_toggled)
        self._pop_section_layout.addWidget(self._pop_carousel)
        self._content_layout.addWidget(self._pop_section)

        # All Apps Grid
        self._all_section = QWidget()
        self._all_section_layout = QVBoxLayout(self._all_section)
        self._all_section_layout.setContentsMargins(0, 0, 0, 0)
        self._all_section_layout.setSpacing(10)
        self._all_head = self._section_head("grid", "Explorar Todo", Theme.text())
        self._all_section_layout.addLayout(self._all_head)
        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(16)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._all_section_layout.addWidget(self._grid_widget)
        self._content_layout.addWidget(self._all_section)

        scroll.setWidget(self._content_widget)
        main_layout.addWidget(scroll, stretch=1)

    def _section_head(self, icon, title, color) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        ico = Icon(icon, 18)
        ico.set_color(color)
        row.addWidget(ico)
        lbl = QLabel(title)
        lbl.setFont(get_font(14, weight=700))
        lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        row.addWidget(lbl)
        row.addStretch()
        return row

    def refresh_style(self) -> None:
        self.setStyleSheet(f"QWidget {{ background-color: {Theme.bg()}; }}")
        self._header.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        self._count_label.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        
        self._hero_frame.setStyleSheet(f"background-color: {Theme.card()}; border: 1px solid {Theme.border()}; border-radius: 16px;")
        self._hero_title.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        self._hero_desc.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        
        for head in [self._fav_head, self._pop_head, self._all_head]:
            for i in range(head.count()):
                w = head.itemAt(i).widget()
                if isinstance(w, QLabel):
                    w.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
                elif isinstance(w, Icon) and head != self._fav_head:
                    w.set_color(Theme.text())

        self._update_categories()
        self._render()

    def set_plugins(self, plugins: list[PluginDescriptor]) -> None:
        self._all_plugins = plugins
        self._update_categories()
        self._render()

    def set_favorites(self, fav_ids: list[str]) -> None:
        self._favorite_ids = fav_ids
        self._render()

    def _update_categories(self) -> None:
        while self._cat_layout.count():
            item = self._cat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_btn = self._create_cat_button("Todo", None)
        self._cat_layout.addWidget(all_btn)

        cats = sorted({p.category for p in self._all_plugins}, key=lambda c: c.value)
        for cat in cats:
            btn = self._create_cat_button(cat.value, cat)
            self._cat_layout.addWidget(btn)
        self._cat_layout.addStretch()

    def _create_cat_button(self, text: str, category: PluginCategory | None) -> QWidget:
        is_active = category is None and self._current_category is None or (
            category is not None and self._current_category == category
        )
        btn = QLabel(text)
        btn.setFont(get_font(12))
        btn.setStyleSheet(f"""
            QLabel {{
                padding: 6px 14px;
                border-radius: 14px;
                background-color: {ACCENT + "20" if is_active else Theme.card()};
                color: {ACCENT if is_active else Theme.text_secondary()};
                border: 1px solid {ACCENT + "40" if is_active else Theme.border()};
            }}
        """)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.mousePressEvent = lambda _: self._filter_by_category(category)
        return btn

    def _filter_by_category(self, category: PluginCategory | None) -> None:
        self._current_category = category
        self._update_categories()
        self._render()

    def _on_card_clicked(self, plugin_id: str) -> None:
        self.plugin_clicked.emit(plugin_id)

    def _on_fav_toggled(self, plugin_id: str, is_fav: bool) -> None:
        if is_fav and plugin_id not in self._favorite_ids:
            self._favorite_ids.append(plugin_id)
            self.favorite_toggled.emit(plugin_id, True)
        elif not is_fav and plugin_id in self._favorite_ids:
            self._favorite_ids.remove(plugin_id)
            self.favorite_toggled.emit(plugin_id, False)
        self._render()

    def _render(self) -> None:
        if not self._all_plugins:
            return

        # Setup Hero Banner (featured app)
        featured = next((p for p in self._all_plugins if p.id == "horas_extras"), self._all_plugins[0])
        self._hero_title.setText(featured.name)
        self._hero_desc.setText(featured.description)
        try:
            self._hero_btn.clicked.disconnect()
        except RuntimeError:
            pass
        self._hero_btn.clicked.connect(lambda: self._on_card_clicked(featured.id))
        
        plugins = self._all_plugins
        if self._current_category:
            plugins = [p for p in plugins if p.category == self._current_category]

        total = len(self._all_plugins)
        count_text = f"{total} herramienta{'s' if total != 1 else ''} disponibles"
        if self._current_category:
            count_text += f" · {self._current_category.value}"
        self._count_label.setText(count_text)

        # Favorites
        fav_plugins = [p for p in self._all_plugins if p.id in self._favorite_ids]
        self._fav_section.setVisible(bool(fav_plugins))
        if fav_plugins:
            self._fav_carousel.set_items(fav_plugins, self._favorite_ids)

        # Popular (Top 5 by execution_count)
        pop_plugins = sorted(self._all_plugins, key=lambda x: x.execution_count, reverse=True)[:5]
        self._pop_carousel.set_items(pop_plugins, self._favorite_ids)

        # All grid
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not plugins:
            empty = QLabel("No hay herramientas en esta categoría.")
            empty.setFont(get_font(13))
            empty.setStyleSheet(f"color: {Theme.text_muted()}; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid_layout.addWidget(empty, 0, 0, 1, 3)
            return

        cols = 3
        for i, plugin in enumerate(plugins):
            is_fav = plugin.id in self._favorite_ids
            card = AppCard(
                plugin_id=plugin.id,
                name=plugin.name,
                description=plugin.description,
                category=plugin.category.value,
                execution_count=plugin.execution_count,
                is_favorite=is_fav,
                icon_name=plugin.icon or "package",
                logo_path=plugin.logo,
                on_click=lambda pid: self._on_card_clicked(pid),
            )
            card._fav_btn.clicked.connect(
                lambda _, pid=plugin.id, fav=is_fav: self._on_fav_toggled(pid, not fav)
            )
            row = i // cols
            col = i % cols
            self._grid_layout.addWidget(card, row, col)
