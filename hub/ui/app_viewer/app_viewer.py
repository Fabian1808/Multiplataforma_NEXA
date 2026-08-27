"""UI — App Viewer. Muestra la interfaz de un plugin dentro del Hub."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QStackedWidget,
)

from hub.core.plugin_registry import PluginRegistry
from hub.models.plugin import PluginDescriptor
from hub.ui.common.design import (
    NEXAStyles,
    ACCENT,
    DARK,
    SURFACE,
    SURFACE_VARIANT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    get_font,
)

logger = logging.getLogger(__name__)


class AppViewer(QWidget):
    """Muestra la ficha de una aplicación y su widget embebido."""

    back_clicked = Signal()
    favorite_toggled = Signal(str, bool)

    def __init__(self, registry: PluginRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._registry = registry
        self._current_plugin: PluginDescriptor | None = None
        self._is_favorite = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._header = QFrame()
        self._header.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE};
                border-bottom: 1px solid #E0E0E0;
                padding: 16px 24px;
            }}
        """)
        header_layout = QVBoxLayout(self._header)
        header_layout.setContentsMargins(24, 16, 24, 16)
        header_layout.setSpacing(8)

        top_row = QHBoxLayout()
        self._back_btn = QPushButton("\u2190 Volver")
        self._back_btn.setStyleSheet(NEXAStyles.secondary_button())
        self._back_btn.setFixedWidth(100)
        self._back_btn.clicked.connect(lambda: self.back_clicked.emit())
        top_row.addWidget(self._back_btn)
        top_row.addStretch()
        self._fav_btn = QPushButton("\u2b50 Favorito")
        self._fav_btn.setStyleSheet(NEXAStyles.secondary_button())
        self._fav_btn.setFixedWidth(120)
        self._fav_btn.clicked.connect(self._toggle_favorite)
        top_row.addWidget(self._fav_btn)
        header_layout.addLayout(top_row)

        self._title = QLabel("")
        self._title.setFont(get_font(20, bold=True))
        self._title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        header_layout.addWidget(self._title)

        self._description = QLabel("")
        self._description.setFont(get_font(12))
        self._description.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._description.setWordWrap(True)
        header_layout.addWidget(self._description)

        meta_row = QHBoxLayout()
        self._status_badge = QLabel("")
        self._status_badge.setFont(get_font(10, bold=True))
        meta_row.addWidget(self._status_badge)
        self._version_label = QLabel("")
        self._version_label.setFont(get_font(11))
        self._version_label.setStyleSheet(f"color: {TEXT_MUTED};")
        meta_row.addWidget(self._version_label)
        self._owner_label = QLabel("")
        self._owner_label.setFont(get_font(11))
        self._owner_label.setStyleSheet(f"color: {TEXT_MUTED};")
        meta_row.addWidget(self._owner_label)
        meta_row.addStretch()
        header_layout.addLayout(meta_row)

        actions_row = QHBoxLayout()
        self._execute_btn = QPushButton("\u25b6  EJECUTAR")
        self._execute_btn.setStyleSheet(NEXAStyles.primary_button())
        self._execute_btn.setFixedWidth(180)
        self._execute_btn.setFixedHeight(40)
        self._execute_btn.clicked.connect(self._on_execute)
        actions_row.addWidget(self._execute_btn)
        actions_row.addStretch()
        header_layout.addLayout(actions_row)

        main_layout.addWidget(self._header)

        self._content_stack = QStackedWidget()
        self._plugin_container = QWidget()
        self._plugin_layout = QVBoxLayout(self._plugin_container)
        self._plugin_layout.setContentsMargins(24, 16, 24, 16)
        self._plugin_layout.setSpacing(0)
        self._placeholder = QLabel("La interfaz del plugin se cargará aquí")
        self._placeholder.setFont(get_font(13))
        self._placeholder.setStyleSheet(f"color: {TEXT_MUTED}; padding: 40px;")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._plugin_layout.addWidget(self._placeholder)
        self._content_stack.addWidget(self._plugin_container)
        self._content_stack.addWidget(self._create_error_widget())
        main_layout.addWidget(self._content_stack, stretch=1)

    def _create_error_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel("\u274c Error al cargar la aplicación")
        label.setFont(get_font(16, bold=True))
        label.setStyleSheet(f"color: #D32F2F;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        self._error_detail = QLabel("")
        self._error_detail.setFont(get_font(11))
        self._error_detail.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._error_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_detail.setWordWrap(True)
        layout.addWidget(self._error_detail)
        retry_btn = QPushButton("Reintentar")
        retry_btn.setStyleSheet(NEXAStyles.primary_button())
        retry_btn.setFixedWidth(120)
        retry_btn.clicked.connect(self._retry_load)
        layout.addWidget(retry_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        return w

    def load_plugin(self, plugin_id: str) -> None:
        desc = self._registry.get(plugin_id)
        if not desc:
            self._show_error(f"Plugin no encontrado: {plugin_id}")
            return

        self._current_plugin = desc
        self._title.setText(desc.name)
        self._description.setText(desc.description)
        self._version_label.setText(f"v{desc.version}")
        self._owner_label.setText(f"Owner: {desc.owner}")

        from hub.ui.common.design import PLUGIN_STATUS_BADGES
        label, color = PLUGIN_STATUS_BADGES.get(desc.status.value, ("Desconocido", TEXT_MUTED))
        self._status_badge.setText(f"  {label} ")
        self._status_badge.setStyleSheet(f"""
            background-color: {color}20;
            color: {color};
            border: 1px solid {color}40;
            border-radius: 4px;
            padding: 2px 8px;
        """)

        self._content_stack.setCurrentIndex(0)

        try:
            self._load_plugin_widget(desc)
        except Exception as e:
            logger.exception("Error cargando widget del plugin %s", plugin_id)
            self._show_error(str(e))

    def _load_plugin_widget(self, desc: PluginDescriptor) -> None:
        while self._plugin_layout.count():
            item = self._plugin_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        factory = self._registry.get_factory(desc.id)
        if factory:
            widget = factory.create_widget(self._plugin_container)
            self._plugin_layout.addWidget(widget)
            return

        try:
            module = self._registry.load_plugin_module(desc.id)
            if hasattr(module, "create_widget"):
                widget = module.create_widget(self._plugin_container)
                self._plugin_layout.addWidget(widget)
            else:
                info = QLabel(f"Módulo cargado: {desc.entrypoint}\nNo se encontró create_widget()")
                info.setFont(get_font(12))
                info.setStyleSheet(f"color: {TEXT_SECONDARY}; padding: 20px;")
                info.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._plugin_layout.addWidget(info)
        except Exception as e:
            info = QLabel(f"No se pudo cargar el módulo: {e}")
            info.setFont(get_font(12))
            info.setStyleSheet(f"color: #D32F2F; padding: 20px;")
            info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._plugin_layout.addWidget(info)

    def _show_error(self, message: str) -> None:
        self._error_detail.setText(message)
        self._content_stack.setCurrentIndex(1)

    def _retry_load(self) -> None:
        if self._current_plugin:
            self.load_plugin(self._current_plugin.id)

    def _toggle_favorite(self) -> None:
        if self._current_plugin:
            self._is_favorite = not self._is_favorite
            self._fav_btn.setText("\u2605 Favorito" if self._is_favorite else "\u2b50 Favorito")
            self.favorite_toggled.emit(self._current_plugin.id, self._is_favorite)

    def _on_execute(self) -> None:
        if self._current_plugin:
            logger.info("Ejecutando plugin: %s", self._current_plugin.id)
            self._execute_btn.setEnabled(False)
            self._execute_btn.setText("Ejecutando...")

            try:
                factory = self._registry.get_factory(self._current_plugin.id)
                if factory:
                    widget = factory.create_widget(self._plugin_container)
                    self._plugin_layout.addWidget(widget)
                    self._execute_btn.setText("\u25b6  EJECUTAR")
                    self._execute_btn.setEnabled(True)
                else:
                    self._execute_btn.setText("\u25b6  EJECUTAR")
                    self._execute_btn.setEnabled(True)
            except Exception as e:
                logger.exception("Error ejecutando plugin %s", self._current_plugin.id)
                self._show_error(str(e))
                self._execute_btn.setText("\u25b6  EJECUTAR")
                self._execute_btn.setEnabled(True)
