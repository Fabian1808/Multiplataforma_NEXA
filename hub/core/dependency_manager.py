"""Gestor de Dependencias de Plugins.

Permite verificar e instalar dinámicamente dependencias usando pip.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from importlib.metadata import version, PackageNotFoundError

logger = logging.getLogger(__name__)


class MissingDependenciesError(Exception):
    """Excepción lanzada cuando faltan dependencias para ejecutar un plugin."""
    def __init__(self, missing_packages: list[str], plugin_id: str):
        self.missing_packages = missing_packages
        self.plugin_id = plugin_id
        super().__init__(f"Faltan dependencias para '{plugin_id}': {', '.join(missing_packages)}")


class DependencyManager:
    """Clase estática para validar e instalar dependencias usando el intérprete actual."""

    @staticmethod
    def get_missing_dependencies(packages: list[str]) -> list[str]:
        """Comprueba qué paquetes de la lista no están instalados en el entorno."""
        import sys
        if getattr(sys, "frozen", False):
            # En modo compilado, asumimos que todo se empaquetó. No podemos usar pip.
            return []
            
        missing = []
        for pkg in packages:
            # Quitamos versiones o extras si las hubiera (ej. "pandas>=1.0") para chequear el nombre base.
            base_pkg = pkg.split(">")[0].split("<")[0].split("=")[0].split("[")[0].strip()
            try:
                version(base_pkg)
            except PackageNotFoundError:
                missing.append(pkg)
        return missing

    @staticmethod
    def install_dependencies(packages: list[str]) -> bool:
        """Ejecuta pip install de manera síncrona para instalar los paquetes dados."""
        if not packages:
            return True

        logger.info("Iniciando instalación automática de dependencias: %s", packages)
        try:
            # Usar python -m pip para asegurar que instalamos en el mismo env.
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", *packages],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("Instalación completada exitosamente.")
            logger.debug(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Fallo al instalar dependencias. Código: %s\nSalida: %s\nError: %s",
                         e.returncode, e.stdout, e.stderr)
            return False
