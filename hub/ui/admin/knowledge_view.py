"""UI — Knowledge Base View. Biblioteca de conocimiento práctico."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hub.ui.common.design import (
    NEXAStyles, ACCENT, get_font,
)


class KnowledgeBaseView(QWidget):
    """Biblioteca de conocimiento con artículos prácticos."""

    article_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._articles: list[dict] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        header = QLabel("Base de Conocimiento")
        header.setFont(get_font(20, bold=True))
        header.setStyleSheet(f"color: {Theme.text()};")
        main_layout.addWidget(header)

        subtitle = QLabel("Soluciones, guías y mejores prácticas para tareas comunes.")
        subtitle.setFont(get_font(12))
        subtitle.setStyleSheet(f"color: {Theme.text_secondary()};")
        main_layout.addWidget(subtitle)

        search_row = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Buscar artículos...")
        self._search_input.setFont(get_font(12))
        self._search_input.setStyleSheet(NEXAStyles.search_input())
        self._search_input.textChanged.connect(self._filter_articles)
        search_row.addWidget(self._search_input, stretch=1)
        main_layout.addLayout(search_row)

        self._current_category: str = ""
        categories = ["Todos", "Excel", "Power BI", "SAP", "Python", "Automatización", "Procesos", "Buenas prácticas"]
        cat_row = QHBoxLayout()
        self._cat_labels: list[QLabel] = []
        for i, cat in enumerate(categories):
            lbl = QLabel(cat)
            lbl.setFont(get_font(11))
            lbl.setStyleSheet(f"""
                QLabel {{
                    padding: 4px 12px;
                    border-radius: 12px;
                    background-color: {"#FF550320" if i == 0 else "#F0F0F0"};
                    color: {"#FF5503" if i == 0 else "#666666"};
                    border: 1px solid {"#FF550340" if i == 0 else "#E0E0E0"};
                }}
            """)
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            lbl.mousePressEvent = lambda _, c=cat, idx=i: self._on_category_click(c, idx)
            cat_row.addWidget(lbl)
            self._cat_labels.append(lbl)
        cat_row.addStretch()
        main_layout.addLayout(cat_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._articles_widget = QWidget()
        self._articles_layout = QVBoxLayout(self._articles_widget)
        self._articles_layout.setSpacing(8)
        scroll.setWidget(self._articles_widget)
        main_layout.addWidget(scroll, stretch=1)

        create_row = QHBoxLayout()
        create_row.addStretch()
        create_btn = QPushButton("Crear Artículo")
        create_btn.setStyleSheet(NEXAStyles.primary_button())
        create_btn.setFixedWidth(180)
        create_row.addWidget(create_btn)
        main_layout.addLayout(create_row)

    def set_articles(self, articles: list[dict]) -> None:
        self._articles = articles
        self._render_articles(articles)

    def _render_articles(self, articles: list[dict]) -> None:
        while self._articles_layout.count():
            item = self._articles_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not articles:
            empty = QLabel("No hay artículos aún. Sé el primero en contribuir.")
            empty.setFont(get_font(13))
            empty.setStyleSheet(f"color: {Theme.text_muted()}; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._articles_layout.addWidget(empty)
            return

        for article in articles:
            aid = article.get("id")
            title = article.get("title") or "Sin título"
            category = article.get("category") or ""
            content = article.get("content") or ""
            author = article.get("author") or ""

            card = QFrame()
            card.setStyleSheet(NEXAStyles.card())
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.mousePressEvent = lambda _, aid=aid: self.article_selected.emit(aid)

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.setSpacing(4)

            title_row = QHBoxLayout()
            title_lbl = QLabel(title)
            title_lbl.setFont(get_font(13, bold=True))
            title_lbl.setStyleSheet(f"color: {Theme.text()};")
            title_row.addWidget(title_lbl, stretch=1)
            if category:
                cat_badge = QLabel(category)
                cat_badge.setFont(get_font(10))
                cat_badge.setStyleSheet(f"color: {ACCENT}; background-color: #FF550315; padding: 2px 8px; border-radius: 4px;")
                title_row.addWidget(cat_badge)
            card_layout.addLayout(title_row)

            preview_text = content[:150] + "..." if len(content) > 150 else content
            preview = QLabel(preview_text)
            preview.setFont(get_font(11))
            preview.setStyleSheet(f"color: {Theme.text_secondary()};")
            preview.setWordWrap(True)
            card_layout.addWidget(preview)

            meta_row = QHBoxLayout()
            author_lbl = QLabel(f"Por {author}" if author else "")
            author_lbl.setFont(get_font(10))
            author_lbl.setStyleSheet(f"color: {Theme.text_muted()};")
            meta_row.addWidget(author_lbl)
            meta_row.addStretch()
            card_layout.addLayout(meta_row)

            self._articles_layout.addWidget(card)

        self._articles_layout.addStretch()

    def _filter_articles(self, query: str) -> None:
        if not query.strip() and not self._current_category:
            self._render_articles(self._articles)
            return
        q = query.lower()
        filtered = [
            a for a in self._articles
            if (
                q in (a.get("title") or "").lower()
                or q in (a.get("content") or "").lower()
                or q in (a.get("category") or "").lower()
            )
            and (not self._current_category or self._current_category == "Todos" or (a.get("category") or "") == self._current_category)
        ]
        self._render_articles(filtered)

    def _on_category_click(self, category: str, index: int) -> None:
        self._current_category = "" if category == "Todos" else category
        for i, lbl in enumerate(self._cat_labels):
            is_active = (i == index)
            lbl.setStyleSheet(f"""
                QLabel {{
                    padding: 4px 12px;
                    border-radius: 12px;
                    background-color: {"#FF550320" if is_active else "#F0F0F0"};
                    color: {"#FF5503" if is_active else "#666666"};
                    border: 1px solid {"#FF550340" if is_active else "#E0E0E0"};
                }}
            """)
        self._filter_articles(self._search_input.text())
