"""UI — Rating Widget. Valoración post-ejecución."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hub.ui.common.design import (
    NEXAStyles, ACCENT, get_font,
)


class RatingWidget(QWidget):
    """Widget de valoración que aparece después de ejecutar una herramienta."""

    rated = Signal(str, bool, int)

    def __init__(self, plugin_id: str, plugin_name: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._plugin_id = plugin_id
        self._plugin_name = plugin_name
        self._setup_ui()

    def _setup_ui(self) -> None:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)

        title = QLabel(f"¿Te ayudó {self._plugin_name}?")
        title.setFont(get_font(12, bold=True))
        title.setStyleSheet(f"color: {Theme.text()};")
        layout.addWidget(title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        yes_btn = QPushButton("Sí")
        yes_btn.setStyleSheet(NEXAStyles.primary_button())
        yes_btn.setFixedWidth(100)
        yes_btn.clicked.connect(lambda: self._rate(True))
        btn_row.addWidget(yes_btn)

        no_btn = QPushButton("No")
        no_btn.setStyleSheet(NEXAStyles.secondary_button())
        no_btn.setFixedWidth(100)
        no_btn.clicked.connect(lambda: self._rate(False))
        btn_row.addWidget(no_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        time_row = QHBoxLayout()
        time_lbl = QLabel("¿Cuánto tiempo te ahorró?")
        time_lbl.setFont(get_font(11))
        time_lbl.setStyleSheet(f"color: {Theme.text_secondary()};")
        time_row.addWidget(time_lbl)

        self._time_buttons: list[QPushButton] = []
        time_options = ["< 5 min", "5-30 min", "30-60 min", "1-2 h", "> 2 h"]
        for opt in time_options:
            btn = QPushButton(opt)
            btn.setStyleSheet(NEXAStyles.secondary_button())
            btn.setFixedWidth(80)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, b=btn: self._select_time(b))
            time_row.addWidget(btn)
            self._time_buttons.append(btn)
        time_row.addStretch()
        layout.addLayout(time_row)

        self._thank_label = QLabel("")
        self._thank_label.setFont(get_font(12))
        self._thank_label.setStyleSheet(f"color: {ACCENT}; font-weight: bold;")
        self._thank_label.setVisible(False)
        layout.addWidget(self._thank_label)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(frame)

        self._selected_time = 0

    def _rate(self, helpful: bool) -> None:
        self.rated.emit(self._plugin_id, helpful, self._selected_time)
        self._thank_label.setText("¡Gracias por tu valoración!")
        self._thank_label.setVisible(True)

    def _select_time(self, btn: QPushButton) -> None:
        time_map = {"< 5 min": 3, "5-30 min": 15, "30-60 min": 45, "1-2 h": 90, "> 2 h": 150}
        self._selected_time = time_map.get(btn.text(), 0)
        for b in self._time_buttons:
            b.setChecked(False)
        btn.setChecked(True)
