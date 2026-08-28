"""Tests — App Launcher Service (estrategia híbrida)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from hub.core.app_launcher_service import AppLauncherService, _apps_dir
from hub.models.plugin import PluginCategory, PluginDescriptor


def _ext_desc(**kw) -> PluginDescriptor:
    defaults = dict(
        id="ext_tool",
        name="Herramienta Externa",
        description="",
        version="1.0.0",
        category=PluginCategory.OTHER,
        launch_mode="external",
        executable_name="tool.exe",
        launch_paths=[],
        launch_url="",
    )
    defaults.update(kw)
    return PluginDescriptor(**defaults)


def test_is_external_property() -> None:
    assert _ext_desc().is_external is True
    assert _ext_desc(launch_mode="embedded").is_external is False


def test_installed_not_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    svc = AppLauncherService()
    desc = _ext_desc(executable_name="tool.exe", launch_paths=[str(tmp_path / "nope.exe")])
    assert svc.is_installed(desc) is False
    assert svc.installed_path(desc) is None


def test_installed_via_local_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    bin_path = tmp_path / "tool.exe"
    bin_path.write_bytes(b"MZ")
    desc = _ext_desc(executable_name="tool.exe", launch_paths=[str(bin_path)])
    svc = AppLauncherService()
    assert svc.is_installed(desc) is True
    assert svc.installed_path(desc) == bin_path


def test_install_blocks_and_copies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    src = tmp_path / "orig" / "tool.exe"
    src.parent.mkdir(parents=True)
    src.write_bytes(b"MZ.....")
    desc = _ext_desc(executable_name="tool.exe", launch_paths=[str(src)])
    svc = AppLauncherService()
    ok, msg = svc.install(desc, block=True)
    assert ok is True
    installed = svc.installed_path(desc)
    assert installed is not None
    assert installed.read_bytes() == b"MZ....."


def test_install_missing_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    desc = _ext_desc(executable_name="tool.exe", launch_paths=[str(tmp_path / "missing.exe")])
    svc = AppLauncherService()
    ok, _msg = svc.install(desc, block=True)
    assert ok is False
