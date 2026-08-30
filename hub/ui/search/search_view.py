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

from hub.i18n import tr
from hub.models.plugin import PluginDescriptor
from hub.ui.common.design import (
    Theme,
    AppCard,
    get_font
)


class SearchView(QWidget):
    """Vista de resultados de búsqueda."""

    plugin_clicked = Signal(str)
    article_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._last_query = ""
        self._last_results_count = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        self._header = QLabel("Resultados de Búsqueda")
        self._header.setFont(get_font(20, bold=True))
        self._header.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        main_layout.addWidget(self._header)

        self._query_label = QLabel("")
        self._query_label.setFont(get_font(13))
        self._query_label.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        main_layout.addWidget(self._query_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        self._results_widget = QWidget()
        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setSpacing(12)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self._results_widget)
        main_layout.addWidget(scroll, stretch=1)
        
        self.refresh_style()

    def refresh_style(self) -> None:
        self.setStyleSheet(f"QWidget {{ background-color: {Theme.bg()}; }}")
        self._header.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        self._query_label.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        
        # Actualizar textos
        if self._last_query:
            self._query_label.setText(
                tr("search.results").format(q=self._last_query) + 
                f" ({self._last_results_count})"
            )
        else:
            self._header.setText("Resultados de Búsqueda")

    def show_results(self, query: str, plugin_results: list[tuple[PluginDescriptor, float]], knowledge_results: list[dict] = None) -> None:
        if knowledge_results is None:
            knowledge_results = []
            
        self._last_query = query
        self._last_results_count = len(plugin_results) + len(knowledge_results)
        
        if self._last_results_count > 0:
            self._query_label.setText(tr("search.results").format(q=query) + f" ({self._last_results_count})")
        else:
            self._query_label.setText(tr("search.no_results").format(q=query))

        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._last_results_count == 0:
            empty = QLabel(tr("catalog.empty"))
            empty.setFont(get_font(13))
            empty.setStyleSheet(f"color: {Theme.text_muted()}; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._results_layout.addWidget(empty)
            return

        # ---- Section: Apps ----
        if plugin_results:
            apps_title = QLabel(f"Aplicaciones ({len(plugin_results)})")
            apps_title.setFont(get_font(14, bold=True))
            apps_title.setStyleSheet(f"color: {Theme.text()}; margin-top: 10px;")
            self._results_layout.addWidget(apps_title)
            
            for plugin, score in plugin_results:
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
                score_label.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
                score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                score_label.setFixedWidth(50)
                row.addWidget(score_label)

                container = QWidget()
                container.setLayout(row)
                self._results_layout.addWidget(container)

        # ---- Section: Knowledge ----
        if knowledge_results:
            kb_title = QLabel(f"Base de Conocimiento ({len(knowledge_results)})")
            kb_title.setFont(get_font(14, bold=True))
            kb_title.setStyleSheet(f"color: {Theme.text()}; margin-top: 20px;")
            self._results_layout.addWidget(kb_title)
            
            for art in knowledge_results:
                art_id = art.get("id")
                title = art.get("title", "Sin título")
                summary = art.get("summary") or art.get("content", "")[:100] + "..."
                
                art_card = QFrame()
                art_card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {Theme.card()};
                        border: 1px solid {Theme.border()};
                        border-radius: 8px;
                    }}
                    QFrame:hover {{
                        border-color: #2196F3;
                    }}
                """)
                art_card.setCursor(Qt.CursorShape.PointingHandCursor)
                art_card.mousePressEvent = lambda _, aid=art_id: self.article_clicked.emit(aid)
                
                v_lay = QVBoxLayout(art_card)
                v_lay.setContentsMargins(16, 12, 16, 12)
                
                t_lbl = QLabel(title)
                t_lbl.setFont(get_font(13, bold=True))
                t_lbl.setStyleSheet(f"color: {Theme.text()}; border: none;")
                v_lay.addWidget(t_lbl)
                
                s_lbl = QLabel(summary)
                s_lbl.setFont(get_font(11))
                s_lbl.setStyleSheet(f"color: {Theme.text_secondary()}; border: none;")
                s_lbl.setWordWrap(True)
                v_lay.addWidget(s_lbl)
                
                self._results_layout.addWidget(art_card)

        self._results_layout.addStretch()
