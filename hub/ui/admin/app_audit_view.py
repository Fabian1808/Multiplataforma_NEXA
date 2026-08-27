"""UI — App Audit View. Auditoria visual de herramientas con estado y fallas."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hub.ui.common.design import (
    ACCENT,
    ERROR,
    SUCCESS,
    WARNING,
    NEXAStyles,
    Theme,
    get_font,
    make_shadow,
)

STATE_COLORS = {
    "activo": SUCCESS,
    "pausado": WARNING,
    "mantenimiento": "#E65100",
    "con_problemas": ERROR,
}


class _AuditAppStateCard(QFrame):
    """Tarjeta individual que muestra el estado de una herramienta."""

    def __init__(self, data: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data = data
        self.plugin_id: str = data.get("plugin_id", "")
        self.setObjectName("card")
        self.setStyleSheet(NEXAStyles.card())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(180)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(NEXAStyles.PADDING_CARD, 14, NEXAStyles.PADDING_CARD, 14)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        icon_frame = QFrame()
        icon_frame.setFixedSize(40, 40)
        icon_frame.setStyleSheet(
            f"background-color: {ACCENT}15; border-radius: 8px; border: none;"
        )
        icon_lbl = QLabel("\u2699\ufe0f")
        icon_lbl.setFont(get_font(18))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"color: {ACCENT}; background: transparent; border: none;")
        icon_inner = QVBoxLayout(icon_frame)
        icon_inner.setContentsMargins(0, 0, 0, 0)
        icon_inner.addWidget(icon_lbl)
        top_row.addWidget(icon_frame)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        name_lbl = QLabel(self._data.get("name", ""))
        name_lbl.setFont(get_font(13, bold=True))
        name_lbl.setStyleSheet(
            f"color: {Theme.text()}; background: transparent; border: none;"
        )
        name_lbl.setWordWrap(True)
        info_col.addWidget(name_lbl)
        top_row.addLayout(info_col, stretch=1)
        layout.addLayout(top_row)

        state = self._data.get("state", "activo")
        state_label = state.upper().replace("_", " ")
        state_color = STATE_COLORS.get(state, Theme.text_muted())
        badge = QLabel(state_label)
        badge.setStyleSheet(NEXAStyles.badge(state_label, state_color))

        failure_count = self._data.get("failure_count", 0)
        failure_lbl = QLabel(f"{failure_count} FALLAS")
        failure_lbl.setFont(get_font(11, bold=True))
        fail_color = ERROR if failure_count > 0 else Theme.text_muted()
        failure_lbl.setStyleSheet(
            f"color: {fail_color}; background: transparent; border: none;"
        )
        failure_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        failure_lbl.mousePressEvent = lambda _: self._on_failure_click()

        badge_row = QHBoxLayout()
        badge_row.setSpacing(12)
        badge_row.addWidget(badge)
        badge_row.addWidget(failure_lbl)
        badge_row.addStretch()
        layout.addLayout(badge_row)

        last_exec = self._data.get("last_execution_at", "")
        exec_text = f"\u25b6 \u00daltima ejecuci\u00f3n: {last_exec}" if last_exec else ""
        exec_lbl = QLabel(exec_text)
        exec_lbl.setFont(get_font(10))
        exec_lbl.setStyleSheet(
            f"color: {Theme.text_secondary()}; background: transparent; border: none;"
        )
        layout.addWidget(exec_lbl)

        last_upd = self._data.get("last_update_at", "")
        upd_text = f"\U0001f504 \u00daltima actualizaci\u00f3n: {last_upd}" if last_upd else ""
        upd_lbl = QLabel(upd_text)
        upd_lbl.setFont(get_font(10))
        upd_lbl.setStyleSheet(
            f"color: {Theme.text_muted()}; background: transparent; border: none;"
        )
        layout.addWidget(upd_lbl)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        action_row.addStretch()

        detail_btn = QPushButton("Ver detalle")
        detail_btn.setStyleSheet(NEXAStyles.ghost_button())
        detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        detail_btn.clicked.connect(lambda: self._on_detail_click())
        action_row.addWidget(detail_btn)

        toggle_label = "Reactivar" if state == "pausado" else "Pausar"
        toggle_btn = QPushButton(toggle_label)
        toggle_btn.setStyleSheet(NEXAStyles.secondary_button())
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_btn.setFixedWidth(110)
        action_row.addWidget(toggle_btn)

        layout.addLayout(action_row)

    def _on_failure_click(self) -> None:
        view: AppAuditView | None = self.parentWidget()  # type: ignore[assignment]
        while view is not None and not isinstance(view, AppAuditView):
            view = view.parentWidget()  # type: ignore[assignment]
        if view is not None:
            view.failure_clicked.emit(self.plugin_id)

    def _on_detail_click(self) -> None:
        view: AppAuditView | None = self.parentWidget()  # type: ignore[assignment]
        while view is not None and not isinstance(view, AppAuditView):
            view = view.parentWidget()  # type: ignore[assignment]
        if view is not None:
            view.detail_clicked.emit(self.plugin_id)


class AppAuditView(QWidget):
    """Vista de auditoria visual de herramientas."""

    failure_clicked = Signal(str)
    detail_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._kpi_labels: dict[str, QLabel] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(NEXAStyles.scroll_area())
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(16)

        header = QLabel("\U0001f4ca Auditor\u00eda de Herramientas")
        header.setFont(get_font(20, bold=True))
        header.setStyleSheet(
            f"color: {Theme.text()}; background: transparent; border: none;"
        )
        self._layout.addWidget(header)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        kpi_defs = [
            ("total", "\u2699\ufe0f", "Total", ACCENT),
            ("active", "\u25b6", "Activas", SUCCESS),
            ("paused", "\u23f8", "Pausadas", WARNING),
            ("maintenance", "\U0001f527", "Mantenimiento", "#E65100"),
            ("problems", "\u26a0", "Con Problemas", ERROR),
            ("failures", "\u2716", "Fallas Abiertas", ERROR),
        ]
        for key, icon, title, color in kpi_defs:
            card = self._build_kpi(icon, title, "0", color)
            kpi_row.addWidget(card)
            self._kpi_labels[key] = card.findChild(QLabel, "kpi_val")
        self._layout.addLayout(kpi_row)

        self._grid = QGridLayout()
        self._grid.setSpacing(12)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._layout.addLayout(self._grid)

        self._layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

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

    def _clear_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def set_app_data(self, apps: list[dict]) -> None:
        self._clear_grid()

        total = len(apps)
        active = sum(1 for a in apps if a.get("state") == "activo")
        paused = sum(1 for a in apps if a.get("state") == "pausado")
        maintenance = sum(1 for a in apps if a.get("state") == "mantenimiento")
        problems = sum(1 for a in apps if a.get("state") == "con_problemas")
        failures = sum(a.get("failure_count", 0) for a in apps)

        for key, val in [
            ("total", total),
            ("active", active),
            ("paused", paused),
            ("maintenance", maintenance),
            ("problems", problems),
            ("failures", failures),
        ]:
            lbl = self._kpi_labels.get(key)
            if lbl is not None:
                lbl.setText(str(val))

        for i, data in enumerate(apps):
            card = _AuditAppStateCard(data)
            make_shadow(card, blur=12, offset_y=2)
            self._grid.addWidget(card, i // 2, i % 2)
