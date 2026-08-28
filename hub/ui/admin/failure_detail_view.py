"""UI — Failure Detail View. Detalle de incidencias por herramienta."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from hub.ui.common.design import (
    Theme,
    NEXAStyles,
    ACCENT,
    ERROR,
    SUCCESS,
    WARNING,
    get_font
)

_SEVERITY_COLORS = {
    "critico": ERROR,
    "critica": ERROR,
    "alto": "#E65100",
    "media": WARNING,
    "medio": WARNING,
    "bajo": SUCCESS,
    "baja": SUCCESS,
}

_STATUS_COLORS = {
    "abierto": ERROR,
    "en_progreso": WARNING,
    "resuelto": SUCCESS,
}

_STATUS_LABELS = {
    "abierto": "Abierto",
    "en_progreso": "En Progreso",
    "resuelto": "Resuelto",
}


class FailureDetailView(QWidget):
    """Vista de detalle de incidencias de una herramienta."""

    back_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        back_btn = QPushButton("Volver")
        back_btn.setStyleSheet(NEXAStyles.secondary_button())
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setFixedWidth(100)
        back_btn.clicked.connect(lambda: self.back_clicked.emit())
        top_row.addWidget(back_btn)

        self._title = QLabel("Incidencias")
        self._title.setFont(get_font(20, bold=True))
        self._title.setStyleSheet(
            f"color: {Theme.text()}; background: transparent; border: none;"
        )
        top_row.addWidget(self._title, stretch=1)
        top_row.addStretch()

        layout.addLayout(top_row)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Fecha", "Usuario", "Tipo Error", "Severidad",
            "Estado", "Descripci\u00f3n", "Resoluci\u00f3n",
        ])
        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(NEXAStyles.table())
        layout.addWidget(self._table, stretch=1)

        self._empty_label = QLabel("No hay incidencias registradas para esta herramienta.")
        self._empty_label.setFont(get_font(12))
        self._empty_label.setStyleSheet(
            f"color: {Theme.text_muted()}; background: transparent;"
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setVisible(False)
        layout.addWidget(self._empty_label, stretch=1)

    def _make_badge(self, text: str, color: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(NEXAStyles.badge(text, color))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(lbl)
        return container

    def set_failures(self, failures: list[dict], app_name: str = "") -> None:
        if app_name:
            self._title.setText(f"Incidencias \u2014 {app_name}")

        self._table.setRowCount(len(failures))
        self._empty_label.setVisible(len(failures) == 0)
        self._table.setVisible(len(failures) > 0)

        for i, f in enumerate(failures):
            date_str = f.get("date", f.get("created_at", ""))[:16].replace("T", " ")
            date_item = QTableWidgetItem(date_str)
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 0, date_item)

            user_item = QTableWidgetItem(f.get("user", f.get("user_name", "")))
            user_item.setFlags(user_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 1, user_item)

            error_type = f.get("error_type", f.get("tipo_error", ""))
            error_item = QTableWidgetItem(error_type)
            error_item.setFlags(error_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 2, error_item)

            severity_raw = f.get("severity", f.get("severidad", "")).lower()
            severity_label = severity_raw.upper() if severity_raw else "-"
            severity_color = _SEVERITY_COLORS.get(severity_raw, Theme.text_muted())
            severity_widget = self._make_badge(severity_label, severity_color)
            self._table.setCellWidget(i, 3, severity_widget)
            self._table.setItem(i, 3, QTableWidgetItem(""))

            status_raw = f.get("status", f.get("estado", "")).lower()
            status_label = _STATUS_LABELS.get(status_raw, status_raw.capitalize() if status_raw else "-")
            status_color = _STATUS_COLORS.get(status_raw, Theme.text_muted())
            status_widget = self._make_badge(status_label, status_color)
            self._table.setCellWidget(i, 4, status_widget)
            self._table.setItem(i, 4, QTableWidgetItem(""))

            desc_item = QTableWidgetItem(f.get("description", f.get("descripcion", "")))
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 5, desc_item)

            resolution = f.get("resolution", f.get("resolucion", ""))
            res_item = QTableWidgetItem(resolution if resolution else "Pendiente")
            res_item.setFlags(res_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if not resolution:
                res_item.setForeground(QColor(Theme.text_muted()))
            self._table.setItem(i, 6, res_item)

        for row_idx in range(len(failures)):
            self._table.setRowHeight(row_idx, 42)
