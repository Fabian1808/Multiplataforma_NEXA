"""UI — Notifications View. Centro de notificaciones."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hub.models.notification import Notification
from hub.ui.common.design import (
    NEXAStyles, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, get_font,
)


class NotificationView(QWidget):
    """Centro de notificaciones del usuario."""

    notification_clicked = Signal(int)
    mark_all_read_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._notifications: list[Notification] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        header_row = QHBoxLayout()
        header = QLabel("\U0001f514 Notificaciones")
        header.setFont(get_font(20, bold=True))
        header.setStyleSheet(f"color: {TEXT_PRIMARY};")
        header_row.addWidget(header, stretch=1)
        mark_all_btn = QPushButton("Marcar todo como leído")
        mark_all_btn.setStyleSheet(NEXAStyles.secondary_button())
        mark_all_btn.setFixedWidth(200)
        mark_all_btn.clicked.connect(lambda: self.mark_all_read_clicked.emit())
        header_row.addWidget(mark_all_btn)
        main_layout.addLayout(header_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setSpacing(8)
        scroll.setWidget(self._list_widget)
        main_layout.addWidget(scroll, stretch=1)

    def set_notifications(self, notifications: list[Notification]) -> None:
        self._notifications = notifications
        self._render()

    def _render(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._notifications:
            empty = QLabel("No tienes notificaciones nuevas.")
            empty.setFont(get_font(13))
            empty.setStyleSheet(f"color: {TEXT_MUTED}; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.addWidget(empty)
            return

        type_icons = {
            "nueva_version": "\U0001f504",
            "herramienta_disponible": "\u26a1",
            "solicitud_actualizada": "\U0001f4cb",
            "problema_resuelto": "\u2705",
            "nueva_guia": "\U0001f4da",
            "herramienta_recomendada": "\U0001f4a1",
        }

        for notif in self._notifications:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {"#F0F7FF" if not notif.read else "#FFFFFF"};
                    border: 1px solid {"#90CAF9" if not notif.read else "#E0E0E0"};
                    border-radius: 8px;
                    padding: 12px 16px;
                }}
            """)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.mousePressEvent = lambda _, nid=notif.id: self.notification_clicked.emit(nid)

            card_layout = QHBoxLayout(card)
            card_layout.setSpacing(12)

            icon = type_icons.get(notif.notification_type.value, "\U0001f514")
            icon_lbl = QLabel(icon)
            icon_lbl.setFont(get_font(18))
            card_layout.addWidget(icon_lbl)

            info = QVBoxLayout()
            info.setSpacing(2)
            title = QLabel(notif.title)
            title.setFont(get_font(12, bold=True))
            title.setStyleSheet(f"color: {TEXT_PRIMARY};")
            info.addWidget(title)
            msg = QLabel(notif.message)
            msg.setFont(get_font(11))
            msg.setStyleSheet(f"color: {TEXT_SECONDARY};")
            msg.setWordWrap(True)
            info.addWidget(msg)
            card_layout.addLayout(info, stretch=1)

            if not notif.read:
                unread_dot = QLabel("\u25cf")
                unread_dot.setFont(get_font(10))
                unread_dot.setStyleSheet(f"color: {ACCENT};")
                card_layout.addWidget(unread_dot)

            self._list_layout.addWidget(card)

        self._list_layout.addStretch()
