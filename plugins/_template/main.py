"""Template para nuevos plugins del NEXA Productivity Hub."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


def create_widget(parent: Any = None) -> QWidget:
    widget = QWidget(parent)
    layout = QVBoxLayout(widget)
    label = QLabel("Mi Nueva Herramienta — En desarrollo")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    return widget
