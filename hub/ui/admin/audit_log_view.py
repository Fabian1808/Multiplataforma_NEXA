"""UI — Audit Log. Vista de registro de auditoría."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QHeaderView, QComboBox,
)

from hub.ui.common.design import (
    Theme,
    NEXAStyles,
    ACCENT,
    Icon,
    get_font
)
from hub.i18n import tr


class AuditLogView(QWidget):
    """Vista de registro de auditoría con filtros."""

    load_more_clicked = Signal()

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
        self._header = QLabel("Registro de Auditoría")
        self._header.setFont(get_font(18, bold=True))
        self._header.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        header_row.addWidget(self._header, stretch=1)
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
        self._module_filter.setStyleSheet(NEXAStyles.combo_box())
        self._module_filter.setFixedWidth(140)
        filters_row.addWidget(self._module_filter)

        self._action_filter = QComboBox()
        self._action_filter.addItems(["Todas", "create", "update", "delete", "view", "login", "search", "execute"])
        self._action_filter.setStyleSheet(NEXAStyles.combo_box())
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
        self._stats_label.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        layout.addWidget(self._stats_label)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([tr("audit.date"), tr("audit.user"), tr("audit.action"), tr("audit.module"), tr("audit.entity"), "Detalles"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(NEXAStyles.table())
        layout.addWidget(self._table, stretch=1)
        
        load_more_row = QHBoxLayout()
        load_more_row.addStretch()
        self._load_more_btn = QPushButton("Cargar más")
        self._load_more_btn.setStyleSheet(NEXAStyles.secondary_button())
        self._load_more_btn.setFixedWidth(120)
        self._load_more_btn.setVisible(False) # Default hidden
        self._load_more_btn.clicked.connect(self.load_more_clicked.emit)
        load_more_row.addWidget(self._load_more_btn)
        load_more_row.addStretch()
        layout.addLayout(load_more_row)

    def refresh_style(self) -> None:
        """Re-aplica el tema actual (claro/oscuro)."""
        self.setStyleSheet(f"QWidget {{ background-color: {Theme.bg()}; }}")
        self._header.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        self._stats_label.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        self._search_input.setStyleSheet(NEXAStyles.search_input())
        self._module_filter.setStyleSheet(NEXAStyles.combo_box())
        self._action_filter.setStyleSheet(NEXAStyles.combo_box())
        self._refresh_btn.setStyleSheet(NEXAStyles.primary_button())
        self._table.setStyleSheet(NEXAStyles.table())
        self._table.setHorizontalHeaderLabels([tr("audit.date"), tr("audit.user"), tr("audit.action"), tr("audit.module"), tr("audit.entity"), "Detalles"])
        
        # Actualizar colores de las filas si es necesario
        for i in range(self._table.rowCount()):
            action_item = self._table.item(i, 2)
            if action_item:
                action_colors = {
                    "create": "#2E7D32", "delete": "#D32F2F", "login": "#1565C0",
                    "update": "#F9A825", "view": "#666666",
                }
                color = action_colors.get(action_item.text().lower(), Theme.text_muted())
                action_item.setForeground(QColor(color))

    def set_entries(self, entries: list[dict], total_count: int = 0, append: bool = False) -> None:
        start_row = self._table.rowCount() if append else 0
        if not append:
            self._table.setRowCount(0)
            self._table.setRowCount(len(entries))
        else:
            self._table.setRowCount(start_row + len(entries))
            
        current_count = start_row + len(entries)
        self._stats_label.setText(f"Mostrando {current_count} de {total_count} registros")
        
        self._load_more_btn.setVisible(current_count < total_count)
        
        for i, entry in enumerate(entries):
            row = start_row + i
            date_str = entry.get("created_at", "")[:16].replace("T", " ")
            self._table.setItem(row, 0, QTableWidgetItem(date_str))
            user_name = entry.get("user_name", entry.get("user_id", ""))
            self._table.setItem(row, 1, QTableWidgetItem(str(user_name)))
            
            action_val = entry.get("action", "")
            action_item = QTableWidgetItem(action_val)
            action_colors = {
                "create": "#2E7D32", "delete": "#D32F2F", "login": "#1565C0",
                "update": "#F9A825", "view": "#666666",
            }
            color = action_colors.get(action_val, Theme.text_muted())
            action_item.setForeground(QColor(color))
            self._table.setItem(row, 2, action_item)
            
            self._table.setItem(row, 3, QTableWidgetItem(entry.get("module", "")))
            entity = f"{entry.get('entity_type', '')} / {entry.get('entity_name', '')}"
            self._table.setItem(row, 4, QTableWidgetItem(entity))
            details = entry.get("details", "")
            self._table.setItem(row, 5, QTableWidgetItem(details[:80] if details else ""))
            
        if current_count == 0:
            self._table.setRowCount(1)
            empty_item = QTableWidgetItem("No hay registros de auditoría")
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setSpan(0, 0, 1, 6)
            self._table.setItem(0, 0, empty_item)
