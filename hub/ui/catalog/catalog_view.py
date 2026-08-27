"""UI — Catalog View. Catálogo completo de aplicaciones con favoritos y filtros."""

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
)

from hub.models.plugin import PluginCategory, PluginDescriptor
from hub.ui.common.design import (
    NEXAStyles,
    Theme,
    AppCard,
    ACCENT,
    get_font,
)


class FavoritesBar(QWidget):
    """Barra horizontal scrollable de aplicaciones favoritas."""

    favorite_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._favorite_ids: list[str] = []
        self._plugins: dict[str, PluginDescriptor] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedHeight(130)

        self._row_widget = QWidget()
        self._row_layout = QHBoxLayout(self._row_widget)
        self._row_layout.setContentsMargins(4, 4, 4, 4)
        self._row_layout.setSpacing(12)
        scroll.setWidget(self._row_widget)
        layout.addWidget(scroll)

    def set_favorites(
        self, fav_ids: list[str], plugins: list[PluginDescriptor]
    ) -> None:
        self._favorite_ids = fav_ids
        self._plugins = {p.id: p for p in plugins}
        self._render()

    def _render(self) -> None:
        while self._row_layout.count():
            item = self._row_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for pid in self._favorite_ids:
            plugin = self._plugins.get(pid)
            if plugin is None:
                continue
            card = AppCard(
                plugin_id=plugin.id,
                name=plugin.name,
                description=plugin.description,
                category=plugin.category.value,
                status=plugin.status.value,
                execution_count=plugin.execution_count,
                is_favorite=True,
                on_click=lambda p: self.favorite_clicked.emit(p),
            )
            card.setFixedWidth(220)
            self._row_layout.addWidget(card)

        self._row_layout.addStretch()


class CatalogView(QWidget):
    """Catálogo de todas las aplicaciones disponibles con sección de favoritos."""

    plugin_clicked = Signal(str)
    favorite_toggled = Signal(str, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._all_plugins: list[PluginDescriptor] = []
        self._favorite_ids: list[str] = []
        self._current_category: PluginCategory | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        header = QLabel("Catálogo de Herramientas")
        header.setFont(get_font(20, bold=True))
        header.setStyleSheet(f"color: {Theme.text()};")
        main_layout.addWidget(header)

        self._categories_bar = QScrollArea()
        self._categories_bar.setWidgetResizable(True)
        self._categories_bar.setFixedHeight(45)
        self._categories_bar.setFrameShape(QFrame.Shape.NoFrame)
        self._categories_bar.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._categories_bar.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._cat_container = QWidget()
        self._cat_layout = QHBoxLayout(self._cat_container)
        self._cat_layout.setContentsMargins(0, 0, 0, 0)
        self._cat_layout.setSpacing(8)
        self._categories_bar.setWidget(self._cat_container)
        main_layout.addWidget(self._categories_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(20)

        self._fav_section = QWidget()
        self._fav_section_layout = QVBoxLayout(self._fav_section)
        self._fav_section_layout.setContentsMargins(0, 0, 0, 0)
        self._fav_section_layout.setSpacing(8)
        self._content_layout.addWidget(self._fav_section)

        fav_label = QLabel("★ Mis Favoritos")
        fav_label.setFont(get_font(15, bold=True))
        fav_label.setStyleSheet(f"color: {ACCENT};")
        self._fav_section_layout.addWidget(fav_label)

        self._fav_bar = FavoritesBar()
        self._fav_bar.favorite_clicked.connect(self._on_card_clicked)
        self._fav_section_layout.addWidget(self._fav_bar)
        self._content_layout.addWidget(self._fav_section)

        all_label = QLabel("Todas las Herramientas")
        all_label.setFont(get_font(15, bold=True))
        all_label.setStyleSheet(f"color: {Theme.text()};")
        self._content_layout.addWidget(all_label)

        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(16)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.addWidget(self._grid_widget)

        scroll.setWidget(self._content_widget)
        main_layout.addWidget(scroll, stretch=1)

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

        all_btn = self._create_cat_button("Todos", None)
        self._cat_layout.addWidget(all_btn)

        cats = sorted(
            {p.category for p in self._all_plugins}, key=lambda c: c.value
        )
        for cat in cats:
            btn = self._create_cat_button(cat.value, cat)
            self._cat_layout.addWidget(btn)
        self._cat_layout.addStretch()

    def _create_cat_button(
        self, text: str, category: PluginCategory | None
    ) -> QWidget:
        is_active = category is None and self._current_category is None or (
            category is not None and self._current_category == category
        )
        btn = QLabel(text)
        btn.setFont(get_font(12))
        btn.setStyleSheet(f"""
            QLabel {{
                padding: 6px 14px;
                border-radius: 14px;
                background-color: {ACCENT + "20" if is_active else Theme.surface()};
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

    def _is_favorite(self, plugin_id: str) -> bool:
        return plugin_id in self._favorite_ids

    def _on_card_clicked(self, plugin_id: str) -> None:
        self.plugin_clicked.emit(plugin_id)

    def _on_fav_toggled(self, plugin_id: str) -> None:
        if plugin_id in self._favorite_ids:
            self._favorite_ids.remove(plugin_id)
            self.favorite_toggled.emit(plugin_id, False)
        else:
            self._favorite_ids.append(plugin_id)
            self.favorite_toggled.emit(plugin_id, True)
        self._render()

    def _render(self) -> None:
        has_favorites = bool(
            self._favorite_ids
            and any(pid in [p.id for p in self._all_plugins] for pid in self._favorite_ids)
        )
        self._fav_section.setVisible(has_favorites)
        if has_favorites:
            self._fav_bar.set_favorites(self._favorite_ids, self._all_plugins)

        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        plugins = self._all_plugins
        if self._current_category:
            plugins = [p for p in plugins if p.category == self._current_category]

        if not plugins:
            empty = QLabel("No hay herramientas en esta categoría")
            empty.setFont(get_font(13))
            empty.setStyleSheet(f"color: {Theme.text_muted()}; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid_layout.addWidget(empty, 0, 0, 1, 3)
            return

        cols = 3
        for i, plugin in enumerate(plugins):
            is_fav = self._is_favorite(plugin.id)
            card = AppCard(
                plugin_id=plugin.id,
                name=plugin.name,
                description=plugin.description,
                category=plugin.category.value,
                status=plugin.status.value,
                execution_count=plugin.execution_count,
                is_favorite=is_fav,
                on_click=lambda pid: self._on_card_clicked(pid),
            )
            card._fav_btn.clicked.connect(
                lambda _, pid=plugin.id: self._on_fav_toggled(pid)
            )
            row = i // cols
            col = i % cols
            self._grid_layout.addWidget(card, row, col)
