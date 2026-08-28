"""UI — Feed / Comunidad. Vista del feed corporativo."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QTextEdit, QVBoxLayout, QWidget, QComboBox,
)

from hub.ui.common.design import (
    NEXAStyles, ACCENT, SUCCESS, get_font, Icon,
)


class FeedView(QWidget):
    """Vista del feed/comunidad corporativo."""

    post_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        header_icon = Icon("activity", 18)
        header_icon.set_color(ACCENT)
        header_row.addWidget(header_icon)
        header = QLabel("Comunidad NEXA")
        header.setFont(get_font(18, bold=True))
        header.setStyleSheet(f"color: {Theme.text()};")
        header_row.addWidget(header, stretch=1)

        self._type_filter = QComboBox()
        self._type_filter.addItems(["Todas", "General", "Logro", "Noticia", "Tutorial", "Pregunta"])
        self._type_filter.setStyleSheet(NEXAStyles.secondary_button())
        self._type_filter.setFixedWidth(140)
        header_row.addWidget(self._type_filter)
        layout.addLayout(header_row)

        create_frame = QFrame()
        create_frame.setStyleSheet(NEXAStyles.card())
        create_layout = QVBoxLayout(create_frame)
        create_layout.setSpacing(8)
        self._new_post_input = QTextEdit()
        self._new_post_input.setPlaceholderText("Comparte algo con la comunidad...")
        self._new_post_input.setMaximumHeight(80)
        self._new_post_input.setStyleSheet("border: 1px solid #E0E0E0; border-radius: 6px; padding: 8px; font-size: 12px;")
        create_layout.addWidget(self._new_post_input)
        post_btn_row = QHBoxLayout()
        post_btn_row.addStretch()
        self._post_btn = QPushButton("Publicar")
        self._post_btn.setStyleSheet(NEXAStyles.primary_button())
        self._post_btn.setFixedWidth(120)
        post_btn_row.addWidget(self._post_btn)
        create_layout.addLayout(post_btn_row)
        layout.addWidget(create_frame)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._posts_container = QWidget()
        self._posts_layout = QVBoxLayout(self._posts_container)
        self._posts_layout.setSpacing(12)
        self._posts_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self._posts_container)
        layout.addWidget(scroll, stretch=1)

    def set_posts(self, posts: list[dict]) -> None:
        while self._posts_layout.count():
            item = self._posts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for post in posts:
            card = QFrame()
            card.setObjectName("card")
            card.setStyleSheet(NEXAStyles.card())
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.setSpacing(8)

            top_row = QHBoxLayout()
            avatar_frame = QFrame()
            avatar_frame.setFixedSize(36, 36)
            avatar_frame.setStyleSheet(f"background-color: {ACCENT}20; border-radius: 18px;")
            av_lay = QHBoxLayout(avatar_frame)
            av_lay.setContentsMargins(0, 0, 0, 0)
            avatar = Icon("user", 16)
            avatar.set_color(ACCENT)
            av_lay.addWidget(avatar)
            top_row.addWidget(avatar_frame)

            author_info = QVBoxLayout()
            author_info.setSpacing(1)
            author = QLabel(post.get("author_name", "Anónimo"))
            author.setFont(get_font(12, bold=True))
            author.setStyleSheet(f"color: {Theme.text()};")
            author_info.addWidget(author)
            meta = f"{post.get('author_area', '')} · {post.get('created_at', '')[:10]}"
            meta_lbl = QLabel(meta)
            meta_lbl.setFont(get_font(9))
            meta_lbl.setStyleSheet(f"color: {Theme.text_muted()};")
            author_info.addWidget(meta_lbl)
            top_row.addLayout(author_info, stretch=1)

            type_label = post.get("post_type", "general")
            type_colors = {"logro": SUCCESS, "noticia": ACCENT, "tutorial": "#1565C0", "pregunta": "#F9A825"}
            color = type_colors.get(type_label, Theme.text_muted())
            badge = QLabel(post.get("type_label", type_label).capitalize() if hasattr(post.get("type_label", ""), "__call__") else type_label.capitalize())
            badge.setStyleSheet(NEXAStyles.badge(type_label.capitalize(), color))
            top_row.addWidget(badge)
            card_layout.addLayout(top_row)

            if post.get("title"):
                title = QLabel(post["title"])
                title.setFont(get_font(13, bold=True))
                title.setStyleSheet(f"color: {Theme.text()};")
                card_layout.addWidget(title)

            content = QLabel(post.get("content", ""))
            content.setFont(get_font(11))
            content.setStyleSheet(f"color: {Theme.text_secondary()};")
            content.setWordWrap(True)
            card_layout.addWidget(content)

            bottom_row = QHBoxLayout()
            likes = post.get("likes_count", 0)
            like_btn = QPushButton(f"Me gusta · {likes}")
            like_btn.setStyleSheet("border: none; color: #999999; font-size: 11px; padding: 2px 6px;")
            like_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            bottom_row.addWidget(like_btn)
            comments = post.get("comments_count", 0)
            comment_btn = QPushButton(f"Comentarios · {comments}")
            comment_btn.setStyleSheet("border: none; color: #999999; font-size: 11px; padding: 2px 6px;")
            comment_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            bottom_row.addWidget(comment_btn)
            bottom_row.addStretch()
            card_layout.addLayout(bottom_row)

            self._posts_layout.addWidget(card)

        if not posts:
            empty = QLabel("No hay publicaciones aún. Sé el primero en compartir.")
            empty.setFont(get_font(14))
            empty.setStyleSheet(f"color: {Theme.text_muted()}; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._posts_layout.addWidget(empty)
