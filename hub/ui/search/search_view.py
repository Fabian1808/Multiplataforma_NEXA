"""UI — Search View. Resultados de búsqueda."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hub.models.plugin import PluginDescriptor
from hub.ui.common.design import (
    Theme,
    AppCard,
    get_font
)


class SearchView(QWidget):
    """Vista de resultados de búsqueda."""

    plugin_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        header = QLabel("Resultados de Búsqueda")
        header.setFont(get_font(20, bold=True))
        header.setStyleSheet(f"color: {Theme.text()};")
        main_layout.addWidget(header)

        self._query_label = QLabel("")
        self._query_label.setFont(get_font(13))
        self._query_label.setStyleSheet(f"color: {Theme.text_secondary()};")
        main_layout.addWidget(self._query_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._results_widget = QWidget()
        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setSpacing(12)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self._results_widget)
        main_layout.addWidget(scroll, stretch=1)

    def show_results(self, query: str, results: list[tuple[PluginDescriptor, float]]) -> None:
        self._query_label.setText(f'Se encontraron {len(results)} resultado(s) para "{query}"')

        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not results:
            empty = QLabel("No se encontraron resultados. Intenta con otros términos.")
            empty.setFont(get_font(13))
            empty.setStyleSheet(f"color: {Theme.text_muted()}; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._results_layout.addWidget(empty)
            return

        for plugin, score in results:
            row = QHBoxLayout()
            row.setSpacing(12)

            card = AppCard(
                plugin_id=plugin.id,
                name=plugin.name,
                description=plugin.description,
                category=plugin.category.value,
                status=plugin.status.value,
                on_click=lambda pid: self.plugin_clicked.emit(pid),
            )
            card.setFixedHeight(100)
            row.addWidget(card, stretch=1)

            score_label = QLabel(f"{score:.0%}")
            score_label.setFont(get_font(11))
            score_label.setStyleSheet(f"color: {Theme.text_muted()};")
            score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            score_label.setFixedWidth(50)
            row.addWidget(score_label)

            container = QWidget()
            container.setLayout(row)
            self._results_layout.addWidget(container)

        self._results_layout.addStretch()
