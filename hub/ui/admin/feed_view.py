# -*- coding: utf-8 -*-
"""UI — Feed / Comunidad. Vista del feed corporativo con estilo LinkedIn."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QTextEdit, QVBoxLayout, QWidget, QComboBox,
)

from hub.ui.common.design import (
    Theme,
    NEXAStyles,
    ACCENT,
    Icon,
    SUCCESS,
    get_font
)


class _PostCard(QFrame):
    """Tarjeta individual de una publicación con comentarios y likes inline."""
    
    def __init__(self, post: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._post = post
        self._liked = False
        self._comments_visible = False
        self.setObjectName("card")
        self.setStyleSheet(NEXAStyles.card())
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # --- Top Row: Avatar & Info ---
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
        author = QLabel(self._post.get("author_name", "Anónimo"))
        author.setFont(get_font(12, bold=True))
        author.setStyleSheet(f"color: {Theme.text()};")
        author_info.addWidget(author)
        meta = f"{self._post.get('author_area', '')} • {self._post.get('created_at', '')[:10]}"
        meta_lbl = QLabel(meta)
        meta_lbl.setFont(get_font(9))
        meta_lbl.setStyleSheet(f"color: {Theme.text_muted()};")
        author_info.addWidget(meta_lbl)
        top_row.addLayout(author_info, stretch=1)

        type_label = self._post.get("post_type", "general")
        type_colors = {"logro": SUCCESS, "noticia": ACCENT, "tutorial": "#1565C0", "pregunta": "#F9A825"}
        color = type_colors.get(type_label.lower(), Theme.text_muted())
        badge = QLabel(self._post.get("type_label", type_label).capitalize())
        badge.setStyleSheet(NEXAStyles.badge(type_label.capitalize(), color))
        top_row.addWidget(badge)
        layout.addLayout(top_row)

        # --- Title & Content ---
        if self._post.get("title"):
            title = QLabel(self._post["title"])
            title.setFont(get_font(13, bold=True))
            title.setStyleSheet(f"color: {Theme.text()};")
            layout.addWidget(title)

        content = QLabel(self._post.get("content", ""))
        content.setFont(get_font(11))
        content.setStyleSheet(f"color: {Theme.text_secondary()};")
        content.setWordWrap(True)
        layout.addWidget(content)

        # --- Interaction Buttons (Like / Comment) ---
        bottom_row = QHBoxLayout()
        self._likes_count = self._post.get("likes_count", 0)
        
        # Like Button
        self._like_btn = QPushButton(f"❤ Me gusta ({self._likes_count})")
        self._like_btn.setStyleSheet(self._get_like_style(False))
        self._like_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._like_btn.clicked.connect(self._toggle_like)
        bottom_row.addWidget(self._like_btn)
        
        # Comment Button
        self._comments_count = self._post.get("comments_count", 0)
        self._comment_btn = QPushButton(f"💬 Comentar ({self._comments_count})")
        self._comment_btn.setStyleSheet("border: none; color: #555555; font-size: 12px; font-weight: bold; padding: 4px 8px;")
        self._comment_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._comment_btn.clicked.connect(self._toggle_comments)
        bottom_row.addWidget(self._comment_btn)
        
        bottom_row.addStretch()
        layout.addLayout(bottom_row)

        # --- Comments Section (Hidden by default) ---
        self._comments_widget = QWidget()
        self._comments_layout = QVBoxLayout(self._comments_widget)
        self._comments_layout.setContentsMargins(0, 10, 0, 0)
        
        # Input to add a new comment
        new_comment_lay = QHBoxLayout()
        self._new_comment_input = QLineEdit()
        self._new_comment_input.setPlaceholderText("Escribe un comentario...")
        self._new_comment_input.setStyleSheet("border: 1px solid #CCCCCC; border-radius: 12px; padding: 6px 10px;")
        new_comment_lay.addWidget(self._new_comment_input)
        
        send_btn = QPushButton("Enviar")
        send_btn.setStyleSheet(NEXAStyles.secondary_button())
        send_btn.clicked.connect(self._add_comment)
        new_comment_lay.addWidget(send_btn)
        self._comments_layout.addLayout(new_comment_lay)
        
        # Load existing mock comments if any
        if self._comments_count > 0:
            mock_comment = QLabel("<b>Juan Pérez:</b> Excelente aporte, gracias por compartir.")
            mock_comment.setStyleSheet("background-color: #F0F2F5; border-radius: 8px; padding: 8px;")
            mock_comment.setWordWrap(True)
            self._comments_layout.addWidget(mock_comment)
            
        self._comments_widget.setVisible(False)
        layout.addWidget(self._comments_widget)

    def _get_like_style(self, liked: bool) -> str:
        color = "#E0245E" if liked else "#555555" # Rojo o gris oscuro
        return f"border: none; color: {color}; font-size: 12px; font-weight: bold; padding: 4px 8px;"

    def _toggle_like(self) -> None:
        self._liked = not self._liked
        self._likes_count += 1 if self._liked else -1
        self._like_btn.setText(f"❤ Me gusta ({self._likes_count})")
        self._like_btn.setStyleSheet(self._get_like_style(self._liked))
        
        # Simular tooltip de quienes dieron like
        if self._likes_count > 0:
            self._like_btn.setToolTip("A ti y otras personas les gusta esto" if self._liked else "A otras personas les gusta esto")
        else:
            self._like_btn.setToolTip("")

    def _toggle_comments(self) -> None:
        self._comments_visible = not self._comments_visible
        self._comments_widget.setVisible(self._comments_visible)

    def _add_comment(self) -> None:
        text = self._new_comment_input.text().strip()
        if not text:
            return
            
        # Add a new comment label
        comment_lbl = QLabel(f"<b>Tú:</b> {text}")
        comment_lbl.setStyleSheet("background-color: #E3F2FD; border-radius: 8px; padding: 8px;")
        comment_lbl.setWordWrap(True)
        self._comments_layout.insertWidget(1, comment_lbl) # Insert below the input box
        
        self._new_comment_input.clear()
        self._comments_count += 1
        self._comment_btn.setText(f"💬 Comentar ({self._comments_count})")


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
            card = _PostCard(post)
            self._posts_layout.addWidget(card)

        if not posts:
            empty = QLabel("No hay publicaciones aún. Sé el primero en compartir.")
            empty.setFont(get_font(14))
            empty.setStyleSheet(f"color: {Theme.text_muted()}; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._posts_layout.addWidget(empty)
