"""UI — Dashboard View. Pantalla principal del Hub."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
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
    AppCard,
    Icon,
    SURFACE_VARIANT,
    get_font
)


class DashboardView(QWidget):
    """Vista principal: saludo, buscador, favoritos, recientes, recomendado."""

    plugin_clicked = Signal(str)

    def __init__(self, user_name: str = "Usuario", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._user_name = user_name
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        greeting = QLabel(f"Buenos días, {self._user_name}")
        greeting.setFont(get_font(22, bold=True))
        greeting.setStyleSheet(f"color: {Theme.text()};")
        main_layout.addWidget(greeting)

        subtitle = QLabel("¿Qué necesitas hacer?")
        subtitle.setFont(get_font(14))
        subtitle.setStyleSheet(f"color: {Theme.text_secondary()};")
        main_layout.addWidget(subtitle)

        main_layout.addSpacing(8)

        search_frame = QFrame()
        search_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.surface()};
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 4px;
            }}
            QFrame:focus-within {{
                border-color: #FF5503;
            }}
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(12, 4, 12, 4)
        search_icon = Icon("search", 16)
        search_icon.set_color(Theme.text_muted())
        search_layout.addWidget(search_icon)

        from PySide6.QtWidgets import QLineEdit
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Buscar herramienta, tarea, proceso o solución...")
        self._search_input.setFont(get_font(14))
        self._search_input.setStyleSheet("border: none; background: transparent;")
        self._search_input.returnPressed.connect(self._on_search)
        search_layout.addWidget(self._search_input, stretch=1)
        main_layout.addWidget(search_frame)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 8, 0, 8)
        scroll_layout.setSpacing(16)

        self._favorites_section = self._create_section("Mis herramientas frecuentes")
        scroll_layout.addWidget(self._favorites_section["container"])

        self._recent_section = self._create_section("Recientes")
        scroll_layout.addWidget(self._recent_section["container"])

        self._recommended_section = self._create_section("Recomendado")
        scroll_layout.addWidget(self._recommended_section["container"])

        self._suggest_section = self._create_suggest_section()
        scroll_layout.addWidget(self._suggest_section)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, stretch=1)

    def _create_section(self, title: str) -> dict:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        label = QLabel(title)
        label.setFont(get_font(15, bold=True))
        label.setStyleSheet(f"color: {Theme.text()};")
        layout.addWidget(label)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        cards_container = QWidget()
        cards_container.setLayout(cards_layout)
        layout.addWidget(cards_container)

        return {
            "container": container,
            "cards_layout": cards_layout,
            "cards_container": cards_container,
        }

    def _create_suggest_section(self) -> QWidget:
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.surface()};
                border: 1px dashed #E0E0E0;
                border-radius: 8px;
                padding: 20px;
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setSpacing(8)

        title = QLabel("¿Tienes una tarea repetitiva?")
        title.setFont(get_font(14, bold=True))
        title.setStyleSheet(f"color: {Theme.text()};")
        layout.addWidget(title)

        subtitle = QLabel("Propón una automatización y te ayudamos a construirla")
        subtitle.setFont(get_font(12))
        subtitle.setStyleSheet(f"color: {Theme.text_secondary()};")
        layout.addWidget(subtitle)

        return container

    def _on_search(self) -> None:
        query = self._search_input.text().strip()
        if query:
            self.plugin_clicked.emit(query)

    def set_favorites(self, cards_data: list[dict]) -> None:
        layout = self._favorites_section["cards_layout"]
        self._clear_layout(layout)
        if not cards_data:
            no_favs = QLabel("Marca herramientas como favoritas para verlas aquí")
            no_favs.setFont(get_font(11))
            no_favs.setStyleSheet(f"color: {Theme.text_muted()};")
            layout.addWidget(no_favs)
            return
        for data in cards_data:
            card = AppCard(
                plugin_id=data["id"],
                name=data["name"],
                description=data.get("description", ""),
                category=data.get("category", ""),
                status=data.get("status", "oficial"),
                on_click=lambda pid: self.plugin_clicked.emit(pid),
            )
            card.setFixedWidth(200)
            card.setFixedHeight(140)
            layout.addWidget(card)

    def set_recent(self, cards_data: list[dict]) -> None:
        layout = self._recent_section["cards_layout"]
        self._clear_layout(layout)
        if not cards_data:
            no_recent = QLabel("Tus herramientas utilizadas recientemente aparecerán aquí")
            no_recent.setFont(get_font(11))
            no_recent.setStyleSheet(f"color: {Theme.text_muted()};")
            layout.addWidget(no_recent)
            return
        for data in cards_data:
            card = AppCard(
                plugin_id=data["id"],
                name=data["name"],
                description=data.get("description", ""),
                category=data.get("category", ""),
                status=data.get("status", "oficial"),
                on_click=lambda pid: self.plugin_clicked.emit(pid),
            )
            card.setFixedWidth(200)
            card.setFixedHeight(140)
            layout.addWidget(card)

    def set_recommended(self, cards_data: list[dict]) -> None:
        layout = self._recommended_section["cards_layout"]
        self._clear_layout(layout)
        for data in cards_data:
            card = AppCard(
                plugin_id=data["id"],
                name=data["name"],
                description=data.get("description", ""),
                category=data.get("category", ""),
                status=data.get("status", "oficial"),
                on_click=lambda pid: self.plugin_clicked.emit(pid),
            )
            card.setFixedWidth(200)
            card.setFixedHeight(140)
            layout.addWidget(card)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
