"""Core — Config Service. Configuración centralizada."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG: dict[str, Any] = {
    "app_name": "NEXA Productivity Hub",
    "version": "2.0.0",
    "theme": "light",
    "language": "es",
    "search": {"min_score": 0.2, "max_results": 20},
    "plugins": {"auto_discover": True, "plugins_dir": "plugins"},
    "logging": {"level": "INFO", "max_file_size_mb": 10, "backup_count": 5},
}


class ConfigService:
    """Gestiona la configuración centralizada del Hub."""

    def __init__(self, config_path: Path | None = None) -> None:
        if config_path:
            self._config_path = config_path
        else:
            appdata = os.environ.get("APPDATA", str(Path.home()))
            self._config_path = Path(appdata) / "NEXA" / "ProductivityHub" / "config.json"
        self._config: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if self._config_path.exists():
            try:
                with open(self._config_path, encoding="utf-8") as f:
                    self._config = json.load(f)
                self._validate()
                logger.info("Config cargada: %s", self._config_path)
            except Exception:
                logger.exception("Error cargando config, usando defaults")
                self._config = dict(_DEFAULT_CONFIG)
        else:
            self._config = dict(_DEFAULT_CONFIG)
            self.save()

    def _validate(self) -> None:
        for key, default_val in _DEFAULT_CONFIG.items():
            if key not in self._config:
                self._config[key] = default_val
        if not isinstance(self._config.get("theme"), str):
            self._config["theme"] = _DEFAULT_CONFIG["theme"]
        if not isinstance(self._config.get("language"), str):
            self._config["language"] = _DEFAULT_CONFIG["language"]
        search = self._config.get("search", {})
        if isinstance(search, dict):
            min_score = search.get("min_score", 0.2)
            if not isinstance(min_score, (int, float)) or not (0.0 <= min_score <= 1.0):
                search["min_score"] = 0.2
            max_results = search.get("max_results", 20)
            if not isinstance(max_results, int) or max_results < 1:
                search["max_results"] = 20

    def save(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
        logger.debug("Config guardada: %s", self._config_path)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value: Any = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        keys = key.split(".")
        d = self._config
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
        self.save()

    @property
    def theme(self) -> str:
        return self.get("theme", "light")

    @property
    def language(self) -> str:
        return self.get("language", "es")
