"""Auth — Login view for NEXA Productivity Hub."""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hub.core.auth_service import AuthService
from hub.ui.common.design import (
    ACCENT,
    ACCENT_BG,
    ERROR,
    NEXAStyles,
    Theme,
    get_font,
)

_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 60


class LoginView(QWidget):
    """Full-screen centered login form with rate-limiting."""

    login_success = Signal(dict)
    login_failed = Signal(str)

    def __init__(self, auth_service: AuthService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._auth = auth_service
        self._attempts = 0
        self._locked_until: float = 0.0
        self._password_visible = False

        self._build_ui()
        self._apply_styles()

    # ── UI construction ────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setObjectName("loginView")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("loginCard")
        card.setFixedSize(420, 520)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 36, 40, 36)
        card_layout.setSpacing(0)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor("#00000040"))
        card.setGraphicsEffect(shadow)

        # ── Logo ──────────────────────────────────────────────
        logo = QLabel("NEXA")
        logo.setFont(get_font(38, bold=True))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(f"color: {ACCENT}; background: transparent; border: none;")
        card_layout.addWidget(logo)

        subtitle = QLabel("Productivity Hub")
        subtitle.setFont(get_font(13))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none; margin-bottom: 4px;")
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(32)

        # ── Username field ────────────────────────────────────
        user_label = QLabel("Usuario")
        user_label.setFont(get_font(11, bold=True))
        user_label.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        card_layout.addWidget(user_label)

        card_layout.addSpacing(6)

        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("Ingresa tu usuario")
        self._username_input.setFixedHeight(44)
        card_layout.addWidget(self._username_input)

        card_layout.addSpacing(18)

        # ── Password field ────────────────────────────────────
        pass_label = QLabel("Contraseña")
        pass_label.setFont(get_font(11, bold=True))
        pass_label.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        card_layout.addWidget(pass_label)

        card_layout.addSpacing(6)

        pass_row = QHBoxLayout()
        pass_row.setContentsMargins(0, 0, 0, 0)
        pass_row.setSpacing(0)

        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setPlaceholderText("Ingresa tu contraseña")
        self._password_input.setFixedHeight(44)
        pass_row.addWidget(self._password_input)

        self._toggle_btn = QPushButton("\U0001f441")
        self._toggle_btn.setFixedSize(44, 44)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setFont(get_font(16))
        self._toggle_btn.clicked.connect(self._toggle_password)
        pass_row.addWidget(self._toggle_btn)

        card_layout.addLayout(pass_row)

        card_layout.addSpacing(8)

        # ── Error label ───────────────────────────────────────
        self._error_label = QLabel("")
        self._error_label.setFont(get_font(11))
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(
            f"color: {ERROR}; background: {ERROR}12; border: 1px solid {ERROR}40; "
            f"border-radius: 6px; padding: 8px 12px; margin-top: 4px;"
        )
        self._error_label.hide()
        card_layout.addWidget(self._error_label)

        card_layout.addSpacing(16)

        # ── Login button ──────────────────────────────────────
        self._login_btn = QPushButton("Iniciar Sesión")
        self._login_btn.setFixedHeight(46)
        self._login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._login_btn.clicked.connect(self._on_login)
        card_layout.addWidget(self._login_btn)

        card_layout.addStretch()

        # ── Footer ────────────────────────────────────────────
        footer = QLabel("NEXA \u00a9 2026 \u00b7 Productivity Hub")
        footer.setFont(get_font(9))
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        card_layout.addWidget(footer)

        outer.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def _apply_styles(self) -> None:
        input_style = NEXAStyles.search_input().replace(
            "border-radius: 8px", "border-radius: 6px"
        )
        self.setStyleSheet(f"""
            #loginView {{
                background-color: {Theme.bg()};
            }}
            #loginCard {{
                background-color: {Theme.card()};
                border: 1px solid {Theme.border()};
                border-radius: 16px;
            }}
            QLineEdit {{
                {input_style}
            }}
            QPushButton#toggleBtn {{
                background: transparent;
                border: none;
                border-radius: 6px;
                color: {Theme.text_muted()};
            }}
            QPushButton#toggleBtn:hover {{
                color: {ACCENT};
                background-color: {Theme.hover_bg()};
            }}
        """)
        self._toggle_btn.setObjectName("toggleBtn")
        self._login_btn.setStyleSheet(NEXAStyles.primary_button())
        self._login_btn.setObjectName("")

    # ── Actions ────────────────────────────────────────────────────

    def _toggle_password(self) -> None:
        self._password_visible = not self._password_visible
        if self._password_visible:
            self._password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._toggle_btn.setText("\U0001f441\ufe0f")
        else:
            self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._toggle_btn.setText("\U0001f441")

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.show()

    def _hide_error(self) -> None:
        self._error_label.hide()
        self._error_label.setText("")

    def _on_login(self) -> None:
        self._hide_error()

        if time.time() < self._locked_until:
            remaining = int(self._locked_until - time.time())
            self._show_error(
                f"Demasiados intentos. Intenta de nuevo en {remaining}s."
            )
            return

        username = self._username_input.text().strip()
        password = self._password_input.text()

        if not username or not password:
            self._show_error("Ingresa usuario y contraseña.")
            return

        user_data = self._auth.authenticate(username, password)

        if user_data is not None:
            self._attempts = 0
            self._locked_until = 0.0
            self.login_success.emit(user_data)
        else:
            self._attempts += 1
            if self._attempts >= _MAX_ATTEMPTS:
                self._locked_until = time.time() + _LOCKOUT_SECONDS
                self._attempts = 0
                self._show_error(
                    f"Cuenta bloqueada temporalmente ({_LOCKOUT_SECONDS}s)."
                )
                self._start_lockout_timer()
            else:
                remaining = _MAX_ATTEMPTS - self._attempts
                self._show_error(
                    f"Credenciales incorrectas. Te quedan {remaining} intento(s)."
                )
            self.login_failed.emit("Credenciales incorrectas")

    def _start_lockout_timer(self) -> None:
        self._lockout_timer = QTimer(self)
        self._lockout_timer.setInterval(1000)
        self._lockout_timer.timeout.connect(self._tick_lockout)
        self._lockout_timer.start()

    def _tick_lockout(self) -> None:
        remaining = self._locked_until - time.time()
        if remaining <= 0:
            self._lockout_timer.stop()
            self._hide_error()
            self._locked_until = 0.0
            return
        self._show_error(
            f"Cuenta bloqueada temporalmente. Reintenta en {int(remaining)}s."
        )
