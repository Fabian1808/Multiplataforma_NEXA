"""UI — Requests View. Lista y detalle de solicitudes con workflow."""

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

from hub.models.request import Request, RequestStatus, RequestPriority
from hub.ui.common.design import (
    NEXAStyles, ACCENT, SUCCESS, WARNING, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, get_font,
)


class RequestsView(QWidget):
    """Lista de solicitudes con estados de workflow."""

    request_selected = Signal(int)

    STATUS_COLORS = {
        RequestStatus.NUEVA: "#1565C0",
        RequestStatus.EN_REVISION: WARNING,
        RequestStatus.EN_DESARROLLO: "#6A1B9A",
        RequestStatus.EN_PRUEBAS: "#00838F",
        RequestStatus.RESUELTA: SUCCESS,
        RequestStatus.CERRADA: TEXT_MUTED,
    }

    PRIORITY_COLORS = {
        RequestPriority.BAJA: SUCCESS,
        RequestPriority.MEDIA: WARNING,
        RequestPriority.ALTA: "#E65100",
        RequestPriority.CRITICA: "#D32F2F",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._requests: list[Request] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        header = QLabel("\U0001f4cb Solicitudes")
        header.setFont(get_font(20, bold=True))
        header.setStyleSheet(f"color: {TEXT_PRIMARY};")
        main_layout.addWidget(header)

        status_row = QHBoxLayout()
        self._status_buttons: list[QPushButton] = []
        all_btn = QPushButton("Todas")
        all_btn.setStyleSheet(NEXAStyles.primary_button())
        all_btn.setFixedWidth(80)
        self._status_buttons.append(("all", all_btn))
        status_row.addWidget(all_btn)
        for status in RequestStatus:
            btn = QPushButton(status.value.replace("_", " ").title())
            btn.setStyleSheet(NEXAStyles.secondary_button())
            btn.setFixedWidth(120)
            self._status_buttons.append((status.value, btn))
            status_row.addWidget(btn)
        status_row.addStretch()
        main_layout.addLayout(status_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setSpacing(8)
        scroll.setWidget(self._list_widget)
        main_layout.addWidget(scroll, stretch=1)

    def set_requests(self, requests: list[Request]) -> None:
        self._requests = requests
        self._render()

    def _render(self, filtered: list[Request] | None = None) -> None:
        items = filtered if filtered is not None else self._requests
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not items:
            empty = QLabel("No hay solicitudes.")
            empty.setFont(get_font(13))
            empty.setStyleSheet(f"color: {TEXT_MUTED}; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.addWidget(empty)
            return

        for req in items:
            card = QFrame()
            card.setStyleSheet(NEXAStyles.card())
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.mousePressEvent = lambda _, rid=req.id: self.request_selected.emit(rid)

            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(4)

            top_row = QHBoxLayout()
            id_lbl = QLabel(f"#{req.id}")
            id_lbl.setFont(get_font(10))
            id_lbl.setStyleSheet(f"color: {TEXT_MUTED};")
            top_row.addWidget(id_lbl)

            status_color = self.STATUS_COLORS.get(req.status, TEXT_MUTED)
            status_lbl = QLabel(req.status.value.replace("_", " ").title())
            status_lbl.setFont(get_font(10, bold=True))
            status_lbl.setStyleSheet(f"color: {status_color}; background-color: {status_color}15; padding: 2px 8px; border-radius: 4px;")
            top_row.addWidget(status_lbl)

            pri_color = self.PRIORITY_COLORS.get(req.priority, TEXT_MUTED)
            pri_lbl = QLabel(req.priority.value.capitalize())
            pri_lbl.setFont(get_font(10))
            pri_lbl.setStyleSheet(f"color: {pri_color};")
            top_row.addWidget(pri_lbl)
            top_row.addStretch()

            if req.owner:
                owner_lbl = QLabel(f"\u2699 {req.owner}")
                owner_lbl.setFont(get_font(10))
                owner_lbl.setStyleSheet(f"color: {TEXT_MUTED};")
                top_row.addWidget(owner_lbl)
            card_layout.addLayout(top_row)

            desc = QLabel(req.description[:200] if req.description else "Sin descripción")
            desc.setFont(get_font(11))
            desc.setStyleSheet(f"color: {TEXT_PRIMARY};")
            desc.setWordWrap(True)
            card_layout.addWidget(desc)

            meta = QLabel(f"Área: {req.area or 'N/A'} · {req.created_at[:10] if req.created_at else 'N/A'}")
            meta.setFont(get_font(10))
            meta.setStyleSheet(f"color: {TEXT_MUTED};")
            card_layout.addWidget(meta)

            self._list_layout.addWidget(card)

        self._list_layout.addStretch()
