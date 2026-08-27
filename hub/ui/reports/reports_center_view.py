"""UI — Reports Center View. Centro de reportes e historial."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QComboBox,
    QSplitter,
)

from hub.ui.common.design import (
    ACCENT,
    ERROR,
    SUCCESS,
    WARNING,
    NEXAStyles,
    Theme,
    get_font,
)

_REPORT_STATUS = {
    "exitoso": ("Exitoso", SUCCESS),
    "error": ("Error", ERROR),
    "pendiente": ("Pendiente", WARNING),
}

_REPORT_TYPE = {
    "general": "General",
    "automatico": "Autom\u00e1tico",
    "semanal": "Semanal",
    "mensual": "Mensual",
}


class ReportsCenterView(QWidget):
    """Centro de reportes con historial, filtros y KPIs."""

    report_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._kpi_labels: dict[str, QLabel] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        header = QLabel("\U0001f4cb Centro de Reportes")
        header.setFont(get_font(20, bold=True))
        header.setStyleSheet(
            f"color: {Theme.text()}; background: transparent; border: none;"
        )
        main_layout.addWidget(header)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        kpi_defs = [
            ("total", "\U0001f4ca", "Total Reportes", ACCENT),
            ("today", "\U0001f4c5", "Hoy", "#1565C0"),
            ("successful", "\u2705", "Exitosos", SUCCESS),
            ("errors", "\u26a0", "Con Error", ERROR),
        ]
        for key, icon, title, color in kpi_defs:
            card = self._build_kpi(icon, title, "0", color)
            kpi_row.addWidget(card)
            self._kpi_labels[key] = card.findChild(QLabel, "kpi_val")
        main_layout.addLayout(kpi_row)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        filter_row.addWidget(self._label_filtro("Herramienta:"))
        self._plugin_combo = QComboBox()
        self._plugin_combo.setStyleSheet(NEXAStyles.combo_box())
        self._plugin_combo.setFixedWidth(160)
        self._plugin_combo.addItem("Todas")
        filter_row.addWidget(self._plugin_combo)

        filter_row.addWidget(self._label_filtro("Usuario:"))
        self._user_combo = QComboBox()
        self._user_combo.setStyleSheet(NEXAStyles.combo_box())
        self._user_combo.setFixedWidth(140)
        self._user_combo.addItem("Todos")
        filter_row.addWidget(self._user_combo)

        filter_row.addWidget(self._label_filtro("Estado:"))
        self._status_combo = QComboBox()
        self._status_combo.setStyleSheet(NEXAStyles.combo_box())
        self._status_combo.setFixedWidth(120)
        self._status_combo.addItems(["Todos", "Exitoso", "Error", "Pendiente"])
        filter_row.addWidget(self._status_combo)

        filter_row.addWidget(self._label_filtro("Tipo:"))
        self._type_combo = QComboBox()
        self._type_combo.setStyleSheet(NEXAStyles.combo_box())
        self._type_combo.setFixedWidth(120)
        self._type_combo.addItems(["Todos", "General", "Autom\u00e1tico", "Semanal", "Mensual"])
        filter_row.addWidget(self._type_combo)

        filter_row.addStretch()

        new_btn = QPushButton("+ Nuevo Reporte")
        new_btn.setStyleSheet(NEXAStyles.primary_button())
        new_btn.setFixedWidth(150)
        filter_row.addWidget(new_btn)

        main_layout.addLayout(filter_row)

        splitter = QSplitter(Qt.Orientation.Vertical)

        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(8)

        self._stats_label = QLabel("")
        self._stats_label.setFont(get_font(11))
        self._stats_label.setStyleSheet(
            f"color: {Theme.text_secondary()}; background: transparent; border: none;"
        )
        table_layout.addWidget(self._stats_label)

        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Herramienta", "Usuario", "Fecha",
            "Estado", "Tipo", "Registros",
        ])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(NEXAStyles.table())
        self._table.verticalHeader().setVisible(False)
        self._table.clicked.connect(self._on_row_clicked)
        table_layout.addWidget(self._table, stretch=1)

        splitter.addWidget(table_container)

        detail_container = QWidget()
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 8, 0, 0)
        detail_layout.setSpacing(8)

        detail_header_row = QHBoxLayout()
        detail_title = QLabel("\U0001f4dd Detalle del Reporte")
        detail_title.setFont(get_font(14, bold=True))
        detail_title.setStyleSheet(
            f"color: {Theme.text()}; background: transparent; border: none;"
        )
        detail_header_row.addWidget(detail_title)
        detail_header_row.addStretch()
        detail_layout.addLayout(detail_header_row)

        self._detail_frame = QFrame()
        self._detail_frame.setStyleSheet(NEXAStyles.card())
        detail_inner = QVBoxLayout(self._detail_frame)
        detail_inner.setSpacing(6)
        detail_inner.setContentsMargins(NEXAStyles.PADDING_CARD, 14, NEXAStyles.PADDING_CARD, 14)

        self._detail_labels: dict[str, QLabel] = {}
        detail_fields = [
            ("id", "ID:"),
            ("name", "Nombre:"),
            ("plugin", "Herramienta:"),
            ("user", "Usuario:"),
            ("date", "Fecha:"),
            ("status", "Estado:"),
            ("type", "Tipo:"),
            ("records", "Registros:"),
        ]
        for key, label_text in detail_fields:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFont(get_font(11, bold=True))
            lbl.setStyleSheet(
                f"color: {Theme.text_secondary()}; background: transparent; border: none;"
            )
            lbl.setFixedWidth(100)
            row.addWidget(lbl)
            val = QLabel("-")
            val.setFont(get_font(11))
            val.setStyleSheet(
                f"color: {Theme.text()}; background: transparent; border: none;"
            )
            row.addWidget(val, stretch=1)
            detail_inner.addLayout(row)
            self._detail_labels[key] = val

        detail_layout.addWidget(self._detail_frame)
        splitter.addWidget(detail_container)

        splitter.setSizes([500, 250])
        main_layout.addWidget(splitter, stretch=1)

    def _label_filtro(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(get_font(11))
        lbl.setStyleSheet(
            f"color: {Theme.text_secondary()}; background: transparent; border: none;"
        )
        return lbl

    def _build_kpi(self, icon: str, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"background-color: {Theme.card()};"
            f" border: 1px solid {Theme.border()};"
            f" border-left: 4px solid {color};"
            f" border-radius: 10px;"
            f" padding: 16px;"
        )
        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        layout.setContentsMargins(16, 14, 16, 14)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(get_font(20))
        icon_lbl.setStyleSheet(
            f"color: {color}; background: transparent; border: none;"
        )
        layout.addWidget(icon_lbl)

        val_lbl = QLabel(value)
        val_lbl.setObjectName("kpi_val")
        val_lbl.setFont(get_font(26, bold=True))
        val_lbl.setStyleSheet(
            f"color: {color}; background: transparent; border: none;"
        )
        layout.addWidget(val_lbl)

        title_lbl = QLabel(title)
        title_lbl.setFont(get_font(11))
        title_lbl.setStyleSheet(
            f"color: {Theme.text_secondary()}; background: transparent; border: none;"
        )
        layout.addWidget(title_lbl)

        return card

    def _on_row_clicked(self, index) -> None:
        row = index.row()
        id_item = self._table.item(row, 0)
        if id_item is not None:
            report_id = int(id_item.text())
            self.report_selected.emit(report_id)
            self._update_detail(row)

    def _update_detail(self, row: int) -> None:
        field_map = {
            0: "id", 1: "name", 2: "plugin", 3: "user",
            4: "date", 5: "status", 6: "type", 7: "records",
        }
        for col, key in field_map.items():
            item = self._table.item(row, col)
            text = item.text() if item else "-"
            lbl = self._detail_labels.get(key)
            if lbl is not None:
                lbl.setText(text)

    def set_reports(self, reports: list[dict]) -> None:
        self._table.setRowCount(len(reports))
        self._stats_label.setText(f"Mostrando {len(reports)} reporte(s)")

        for i, r in enumerate(reports):
            id_item = QTableWidgetItem(str(r.get("id", "")))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 0, id_item)

            name_item = QTableWidgetItem(r.get("name", ""))
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 1, name_item)

            plugin_item = QTableWidgetItem(r.get("plugin", ""))
            plugin_item.setFlags(plugin_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 2, plugin_item)

            user_item = QTableWidgetItem(r.get("user", ""))
            user_item.setFlags(user_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 3, user_item)

            date_item = QTableWidgetItem(r.get("date", ""))
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 4, date_item)

            status_raw = r.get("status", "").lower()
            status_label, status_color = _REPORT_STATUS.get(
                status_raw, (status_raw.capitalize() if status_raw else "-", Theme.text_muted())
            )
            status_container = QWidget()
            status_container.setStyleSheet("background: transparent; border: none;")
            srow = QHBoxLayout(status_container)
            srow.setContentsMargins(0, 0, 0, 0)
            badge = QLabel(status_label)
            badge.setStyleSheet(NEXAStyles.badge(status_label, status_color))
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            srow.addWidget(badge)
            self._table.setCellWidget(i, 5, status_container)
            self._table.setItem(i, 5, QTableWidgetItem(""))

            type_key = r.get("type", "").lower()
            type_label = _REPORT_TYPE.get(type_key, r.get("type", ""))
            type_item = QTableWidgetItem(type_label)
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 6, type_item)

            records_item = QTableWidgetItem(str(r.get("records", "")))
            records_item.setFlags(records_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            records_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(i, 7, records_item)

        for row_idx in range(len(reports)):
            self._table.setRowHeight(row_idx, 40)

    def set_stats(self, stats: dict) -> None:
        mapping = {
            "total": stats.get("total", 0),
            "today": stats.get("today", 0),
            "successful": stats.get("successful", 0),
            "errors": stats.get("errors", 0),
        }
        for key, val in mapping.items():
            lbl = self._kpi_labels.get(key)
            if lbl is not None:
                lbl.setText(str(val))

    def set_plugin_filter(self, plugins: list[str]) -> None:
        self._plugin_combo.clear()
        self._plugin_combo.addItem("Todas")
        self._plugin_combo.addItems(plugins)

    def set_user_filter(self, users: list[str]) -> None:
        self._user_combo.clear()
        self._user_combo.addItem("Todos")
        self._user_combo.addItems(users)
