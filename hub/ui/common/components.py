from __future__ import annotations
import json
import math
import os
import re
from pathlib import Path
from typing import Callable
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QColor, QFont, QPalette, QIcon, QPixmap, QPainter, QPen, QBrush,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget, QGraphicsDropShadowEffect,
)

from .theme import Theme, ACCENT, ACCENT_BG, ACCENT_DARK_BG, is_dark, STATUS_COLORS, PLUGIN_STATUS_BADGES
from .styles import NEXAStyles, get_font
from .icons import Icon

class StatusBadge(QLabel):
    def __init__(self, status: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        label, color = PLUGIN_STATUS_BADGES.get(
            status, (status.capitalize(), Theme.text_muted())
        )
        self.setText(label)
        self.setStyleSheet(NEXAStyles.badge(label, color))
        self.setFixedHeight(22)


class HealthIndicator(QLabel):
    def __init__(self, status: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        color = STATUS_COLORS.get(status, Theme.text_muted())
        self.setText(f"\u25cf {status.capitalize()}")
        self.setStyleSheet(
            f"color: {color}; font-size: 11px; background: transparent; border: none;"
        )


class KPIWidget(QFrame):
    """Tarjeta KPI con barra de color lateral."""

    def __init__(self, title: str, value: str = "0", icon: str = "",
                 color: str = ACCENT, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(NEXAStyles.kpi_card(color))
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(18, 14, 18, 14)

        top = QHBoxLayout()
        if icon:
            ico = Icon(icon, 16)
            ico.set_color(color)
            top.addWidget(ico)
        top.addStretch()
        layout.addLayout(top)

        self._value = QLabel(value)
        self._value.setFont(get_font(26, bold=True))
        self._value.setStyleSheet(
            f"color: {Theme.text()}; background: transparent; border: none;"
        )
        layout.addWidget(self._value)

        self._title = QLabel(title)
        self._title.setFont(get_font(11))
        self._title.setStyleSheet(
            f"color: {Theme.text_secondary()}; background: transparent; border: none;"
        )
        layout.addWidget(self._title)

    def set_value(self, value: str) -> None:
        self._value.setText(value)

    def refresh_style(self, color: str = ACCENT) -> None:
        """Re-aplica la tarjeta y sus textos con el tema activo (claro/oscuro)."""
        self.setStyleSheet(NEXAStyles.kpi_card(color))
        self._value.setStyleSheet(
            f"color: {Theme.text()}; background: transparent; border: none;")
        self._title.setStyleSheet(
            f"color: {Theme.text_secondary()}; background: transparent; border: none;")


class AppCard(QFrame):
    """Tarjeta de aplicación — jerarquía visual clara, hover, favorito y badge."""

    def __init__(self, plugin_id: str, name: str, description: str,
                 category: str = "", status: str = "oficial",
                 execution_count: int = 0, is_favorite: bool = False,
                 icon_name: str = "package", logo_path: str = "",
                 parent: QWidget | None = None,
                 on_click: Callable[[str], None] | None = None) -> None:
        super().__init__(parent)
        self.plugin_id = plugin_id
        self._on_click = on_click
        self._is_fav   = is_favorite
        self.setObjectName("card")
        self.setStyleSheet(NEXAStyles.card_no_hover())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(190)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        # Fila 1: icono + botón favorito
        row1 = QHBoxLayout()
        row1.setSpacing(0)
        icon_bg = ACCENT_BG if not is_dark() else ACCENT_DARK_BG
        icon_frame = QFrame()
        icon_frame.setFixedSize(44, 44)
        icon_frame.setStyleSheet(
            f"background-color: {icon_bg}; border-radius: 11px; border: none;"
        )
        il = QVBoxLayout(icon_frame)
        il.setContentsMargins(0, 0, 0, 0)
        
        if logo_path:
            import os
            from PySide6.QtGui import QPixmap
            pm = QPixmap(logo_path)
            if not pm.isNull():
                pm = pm.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_lbl = QLabel()
                logo_lbl.setPixmap(pm)
                logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                logo_lbl.setStyleSheet("background: transparent; border: none;")
                il.addWidget(logo_lbl, 0, Qt.AlignmentFlag.AlignCenter)
            else:
                icon_lbl = Icon(icon_name, 22)
                icon_lbl.set_color(ACCENT)
                il.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        else:
            icon_lbl = Icon(icon_name, 22)
            icon_lbl.set_color(ACCENT)
            il.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)
            
        row1.addWidget(icon_frame)
        row1.addStretch()

        self._fav_btn = QPushButton()
        self._fav_btn.setFixedSize(30, 30)
        self._fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fav_btn.setStyleSheet(
            f"QPushButton {{ border: none; background: transparent; border-radius: 15px; }}"
            f" QPushButton:hover {{ background-color: {Theme.hover_bg()}; }}"
        )
        self._fav_btn.clicked.connect(self._on_fav_click)
        self._update_fav_icon(is_favorite)
        row1.addWidget(self._fav_btn)
        lay.addLayout(row1)

        # Nombre
        name_lbl = QLabel(name)
        name_lbl.setFont(get_font(14, bold=True))
        name_lbl.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        name_lbl.setWordWrap(True)
        lay.addWidget(name_lbl)

        # Descripción
        desc_text = description[:120] + ("\u2026" if len(description) > 120 else "")
        desc_lbl = QLabel(desc_text)
        desc_lbl.setFont(get_font(11))
        desc_lbl.setStyleSheet(
            f"color: {Theme.text_secondary()}; background: transparent; border: none;"
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setMinimumHeight(36)
        lay.addWidget(desc_lbl)

        lay.addStretch()

        # Footer: categoría + Botón Abrir
        row4 = QHBoxLayout()
        row4.setSpacing(6)
        if category:
            cat_lbl = QLabel(category.capitalize())
            cat_lbl.setFont(get_font(10))
            cat_lbl.setStyleSheet(
                f"color: {Theme.text_muted()}; background: transparent; border: none;"
            )
            row4.addWidget(cat_lbl)
        row4.addStretch()
        
        self._open_btn = QPushButton("Abrir")
        self._open_btn.setFont(get_font(10, bold=True))
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT}15;
                color: {ACCENT};
                border: none;
                border-radius: 12px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT}30;
            }}
        """)
        self._open_btn.clicked.connect(lambda: self._on_click(self.plugin_id) if self._on_click else None)
        row4.addWidget(self._open_btn)
        
        lay.addLayout(row4)

    def _update_fav_icon(self, is_fav: bool) -> None:
        fav_ico = Icon("star", 16, ACCENT if is_fav else Theme.text_muted())
        self._fav_btn.setIcon(QIcon(fav_ico.get_pixmap()))
        self._fav_btn.setIconSize(fav_ico.size())

    def _on_fav_click(self) -> None:
        self._is_fav = not self._is_fav
        self._update_fav_icon(self._is_fav)

    def enterEvent(self, event) -> None:
        self.setStyleSheet(NEXAStyles.card_hover())
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.setStyleSheet(NEXAStyles.card_no_hover())
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if self._on_click:
            self._on_click(self.plugin_id)
        super().mousePressEvent(event)


