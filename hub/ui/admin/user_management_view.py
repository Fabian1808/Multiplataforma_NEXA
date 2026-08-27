"""UI — User Management. Gestión de usuarios y roles."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget, QMessageBox,
)

from hub.ui.common.design import (
    NEXAStyles, ACCENT, SUCCESS, WARNING, ERROR, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, get_font,
)


class UserManagementView(QWidget):
    """Gestión de usuarios del sistema."""

    user_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        header = QLabel("\U0001f465 Gestión de Usuarios")
        header.setFont(get_font(18, bold=True))
        header.setStyleSheet(f"color: {TEXT_PRIMARY};")
        header_row.addWidget(header, stretch=1)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Buscar usuario...")
        self._search.setStyleSheet(NEXAStyles.search_input())
        self._search.setFixedWidth(250)
        header_row.addWidget(self._search)
        layout.addLayout(header_row)

        self._stats_row = QHBoxLayout()
        self._stats_row.setSpacing(16)
        self._total_label = QLabel("Total: 0")
        self._total_label.setFont(get_font(12, bold=True))
        self._stats_row.addWidget(self._total_label)
        self._admin_label = QLabel("Admins: 0")
        self._admin_label.setFont(get_font(12))
        self._admin_label.setStyleSheet(f"color: {ACCENT};")
        self._stats_row.addWidget(self._admin_label)
        self._gestor_label = QLabel("Gestores: 0")
        self._gestor_label.setFont(get_font(12))
        self._gestor_label.setStyleSheet(f"color: {WARNING};")
        self._stats_row.addWidget(self._gestor_label)
        self._stats_row.addStretch()
        layout.addLayout(self._stats_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self._grid = QGridLayout(content)
        self._grid.setSpacing(12)
        self._grid.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

    def set_users(self, users: list[dict]) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total = len(users)
        admins = sum(1 for u in users if "administrador" in u.get("roles", []))
        gestores = sum(1 for u in users if "gestor" in u.get("roles", []))
        self._total_label.setText(f"Total: {total}")
        self._admin_label.setText(f"Admins: {admins}")
        self._gestor_label.setText(f"Gestores: {gestores}")

        for i, user in enumerate(users):
            card = QFrame()
            card.setObjectName("card")
            card.setStyleSheet(NEXAStyles.card())
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.setSpacing(12)

            avatar = QLabel("\U0001f464")
            avatar.setFont(get_font(24))
            avatar.setFixedSize(48, 48)
            avatar.setStyleSheet(f"background-color: {ACCENT}20; border-radius: 24px; color: {ACCENT};")
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(avatar)

            info = QVBoxLayout()
            info.setSpacing(2)
            name_lbl = QLabel(user.get("name", user.get("username", "")))
            name_lbl.setFont(get_font(13, bold=True))
            name_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
            info.addWidget(name_lbl)

            meta = f"{user.get('area', 'Sin área')} · {user.get('email', '')}"
            meta_lbl = QLabel(meta)
            meta_lbl.setFont(get_font(10))
            meta_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
            info.addWidget(meta_lbl)
            card_layout.addLayout(info, stretch=1)

            roles = user.get("roles", [])
            for role in roles:
                role_colors = {"administrador": ACCENT, "gestor": WARNING, "usuario": SUCCESS}
                color = role_colors.get(role, TEXT_MUTED)
                role_lbl = QLabel(role.capitalize())
                role_lbl.setStyleSheet(NEXAStyles.badge(role, color))
                card_layout.addWidget(role_lbl)

            self._grid.addWidget(card, i // 2, i % 2)

        if not users:
            empty = QLabel("No hay usuarios registrados")
            empty.setFont(get_font(14))
            empty.setStyleSheet(f"color: {TEXT_MUTED}; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid.addWidget(empty, 0, 0, 1, 2)
