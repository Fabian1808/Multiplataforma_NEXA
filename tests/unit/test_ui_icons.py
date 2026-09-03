"""Tests — Resolución de iconos SVG de módulos y controles del menú lateral."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


@pytest.fixture(scope="module")
def qt_app():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture(scope="module")
def design(qt_app):
    from hub.ui.common import design
    return design


def test_plugin_icon_returns_svg_for_modules(design):
    for pid in design.PLUGIN_SVG:
        w = design.plugin_icon(pid, 24, "#FF5503")
        assert isinstance(w, design.SvgIcon)
        pm = w.get_pixmap()
        assert not pm.isNull()
        assert pm.width() >= 20


def test_plugin_icon_generic_fallback(design):
    w = design.plugin_icon("plugin_sin_svg", 22, "#FF5503", "folder")
    assert isinstance(w, design.Icon)


def test_mostrar_ocultar_svg_render(design):
    for name in ("mostrar", "ocultar"):
        ico = design.SvgIcon(name, 16, "#333333")
        pm = ico.get_pixmap()
        assert not pm.isNull()
        assert pm.width() > 0


def test_app_card_module_renders(design):
    from hub.ui.common.design import AppCard
    for pid in design.PLUGIN_SVG:
        card = AppCard(
            plugin_id=pid,
            name=f"App {pid}",
            description="Descripción de prueba para la tarjeta del módulo.",
            category="Reporting",
            icon_name="package",
        )
        assert card is not None


def test_app_card_generic_renders(design):
    from hub.ui.common.design import AppCard
    card = AppCard(
        plugin_id="otro",
        name="Otro",
        description="x" * 20,
        category="Otros",
        icon_name="folder",
    )
    assert card is not None
