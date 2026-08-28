"""UI — Audit Log. Vista de registro de auditoría."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QHeaderView, QComboBox,
)

from hub.ui.common.design import (
    NEXAStyles, ACCENT, get_font, Icon,
)


class AuditLogView(QWidget):
    """Vista de registro de auditoría con filtros."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        header_icon = Icon("list", 18)
        header_icon.set_color(ACCENT)
        header_row.addWidget(header_icon)
        header = QLabel("Registro de Auditoría")
        header.setFont(get_font(18, bold=True))
        header.setStyleSheet(f"color: {Theme.text()};")
        header_row.addWidget(header, stretch=1)
        layout.addLayout(header_row)

        filters_row = QHBoxLayout()
        filters_row.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Buscar en auditoría...")
        self._search_input.setStyleSheet(NEXAStyles.search_input())
        self._search_input.setFixedWidth(250)
        filters_row.addWidget(self._search_input)

        self._module_filter = QComboBox()
        self._module_filter.addItems(["Todos", "requests", "knowledge", "plugins", "projects", "feed", "system", "users"])
        self._module_filter.setStyleSheet(NEXAStyles.secondary_button())
        self._module_filter.setFixedWidth(140)
        filters_row.addWidget(self._module_filter)

        self._action_filter = QComboBox()
        self._action_filter.addItems(["Todas", "create", "update", "delete", "view", "login", "search", "execute"])
        self._action_filter.setStyleSheet(NEXAStyles.secondary_button())
        self._action_filter.setFixedWidth(140)
        filters_row.addWidget(self._action_filter)

        self._refresh_btn = QPushButton("Actualizar")
        self._refresh_btn.setStyleSheet(NEXAStyles.primary_button())
        self._refresh_btn.setFixedWidth(120)
        filters_row.addWidget(self._refresh_btn)

        filters_row.addStretch()
        layout.addLayout(filters_row)

        self._stats_label = QLabel("")
        self._stats_label.setFont(get_font(11))
        self._stats_label.setStyleSheet(f"color: {Theme.text_secondary()};")
        layout.addWidget(self._stats_label)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["Fecha", "Usuario", "Acción", "Módulo", "Entidad", "Detalles"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet("""
            QTableWidget { border: 1px solid #E0E0E0; border-radius: 6px; font-size: 12px; }
            QTableWidget::item { padding: 6px; }
            QHeaderView::section { background-color: #F5F5F5; border: none; border-bottom: 2px solid #FF5503; padding: 8px; font-weight: bold; font-size: 11px; }
        """)
        layout.addWidget(self._table, stretch=1)

    def set_entries(self, entries: list[dict], total_count: int = 0) -> None:
        self._table.setRowCount(len(entries))
        self._stats_label.setText(f"Mostrando {len(entries)} de {total_count} registros")
        for i, entry in enumerate(entries):
            date_str = entry.get("created_at", "")[:16].replace("T", " ")
            self._table.setItem(i, 0, QTableWidgetItem(date_str))
            user_name = entry.get("user_name", entry.get("user_id", ""))
            self._table.setItem(i, 1, QTableWidgetItem(str(user_name)))
            action_item = QTableWidgetItem(entry.get("action", ""))
            action_colors = {
                "create": "#2E7D32", "delete": "#D32F2F", "login": "#1565C0",
                "update": "#F9A825", "view": "#666666",
            }
            color = action_colors.get(entry.get("action", ""), Theme.text_muted())
            action_item.setForeground(QColor(color))
            self._table.setItem(i, 2, action_item)
            self._table.setItem(i, 3, QTableWidgetItem(entry.get("module", "")))
            entity = f"{entry.get('entity_type', '')} / {entry.get('entity_name', '')}"
            self._table.setItem(i, 4, QTableWidgetItem(entity))
            details = entry.get("details", "")
            self._table.setItem(i, 5, QTableWidgetItem(details[:80] if details else ""))
        if not entries:
            self._table.setRowCount(1)
            empty_item = QTableWidgetItem("No hay registros de auditoría")
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setSpan(0, 0, 1, 6)
            self._table.setItem(0, 0, empty_item)
