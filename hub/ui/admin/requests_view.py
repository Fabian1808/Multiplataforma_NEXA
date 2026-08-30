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

from hub.ui.common.design import (
    Theme,
    NEXAStyles,
    ACCENT,
    SUCCESS,
    WARNING,
    get_font
)


class RequestsView(QWidget):
    """Lista de solicitudes con estados de workflow."""

    request_selected = Signal(int)

    STATUS_COLORS = {
        "enviada": "#1565C0",
        "en_revision": WARNING,
        "en_desarrollo": "#6A1B9A",
        "pruebas": "#00838F",
        "aprobada": SUCCESS,
        "publicada": SUCCESS,
        "resuelta": SUCCESS,
        "cerrada": Theme.text_muted(),
    }

    PRIORITY_COLORS = {
        "baja": SUCCESS,
        "media": WARNING,
        "alta": "#E65100",
        "critica": "#D32F2F",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._requests: list[dict] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        header = QLabel("Solicitudes")
        header.setFont(get_font(20, bold=True))
        header.setStyleSheet(f"color: {Theme.text()};")
        main_layout.addWidget(header)

        status_row = QHBoxLayout()
        self._status_buttons: list[tuple[str, QPushButton]] = []
        all_btn = QPushButton("Todas")
        all_btn.setStyleSheet(NEXAStyles.primary_button())
        all_btn.setFixedWidth(80)
        all_btn.clicked.connect(lambda: self._filter_by_status("all"))
        self._status_buttons.append(("all", all_btn))
        status_row.addWidget(all_btn)
        for status in ("enviada", "en_revision", "en_desarrollo", "pruebas", "aprobada", "cerrada"):
            btn = QPushButton(status.replace("_", " ").title())
            btn.setStyleSheet(NEXAStyles.secondary_button())
            btn.setFixedWidth(120)
            btn.clicked.connect(lambda _, s=status: self._filter_by_status(s))
            self._status_buttons.append((status, btn))
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

    def set_requests(self, requests: list[dict]) -> None:
        self._requests = requests
        self._filter_by_status("all")

    def _filter_by_status(self, status: str) -> None:
        for s, btn in self._status_buttons:
            if s == status:
                btn.setStyleSheet(NEXAStyles.primary_button())
            else:
                btn.setStyleSheet(NEXAStyles.secondary_button())
                
        if status == "all":
            filtered = self._requests
        else:
            filtered = [r for r in self._requests if r.get("status") == status]
            
        self._render(filtered)

    def _render(self, filtered: list[dict] | None = None) -> None:
        items = filtered if filtered is not None else self._requests
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not items:
            empty = QLabel("No hay solicitudes.")
            empty.setFont(get_font(13))
            empty.setStyleSheet(f"color: {Theme.text_muted()}; padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.addWidget(empty)
            return

        for req in items:
            rid = req.get("id")
            status = req.get("status") or ""
            priority = req.get("priority") or ""

            card = QFrame()
            card.setStyleSheet(NEXAStyles.card())
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.mousePressEvent = lambda _, rid=rid: self.request_selected.emit(rid)

            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(4)

            top_row = QHBoxLayout()
            id_lbl = QLabel(f"#{rid}")
            id_lbl.setFont(get_font(10))
            id_lbl.setStyleSheet(f"color: {Theme.text_muted()};")
            top_row.addWidget(id_lbl)

            status_color = self.STATUS_COLORS.get(status, Theme.text_muted())
            status_lbl = QLabel(status.replace("_", " ").title() if status else "Sin estado")
            status_lbl.setFont(get_font(10, bold=True))
            status_lbl.setStyleSheet(f"color: {status_color}; background-color: {status_color}15; padding: 2px 8px; border-radius: 4px;")
            top_row.addWidget(status_lbl)

            if priority:
                pri_color = self.PRIORITY_COLORS.get(priority, Theme.text_muted())
                pri_lbl = QLabel(priority.capitalize())
                pri_lbl.setFont(get_font(10))
                pri_lbl.setStyleSheet(f"color: {pri_color};")
                top_row.addWidget(pri_lbl)
            top_row.addStretch()

            owner = req.get("owner") or req.get("assigned_to") or req.get("created_by")
            if owner:
                owner_lbl = QLabel(f"{owner}")
                owner_lbl.setFont(get_font(10))
                owner_lbl.setStyleSheet(f"color: {Theme.text_muted()};")
                top_row.addWidget(owner_lbl)
            card_layout.addLayout(top_row)

            desc = QLabel((req.get("description") or "Sin descripción")[:200])
            desc.setFont(get_font(11))
            desc.setStyleSheet(f"color: {Theme.text()};")
            desc.setWordWrap(True)
            card_layout.addWidget(desc)

            area = req.get("area") or "N/A"
            created = (req.get("created_at") or "N/A")[:10]
            meta = QLabel(f"Área: {area} · {created}")
            meta.setFont(get_font(10))
            meta.setStyleSheet(f"color: {Theme.text_muted()};")
            card_layout.addWidget(meta)

            self._list_layout.addWidget(card)

        self._list_layout.addStretch()
