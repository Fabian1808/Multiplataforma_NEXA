"""Núcleo de HORAS EXTRAS MASIVA — orquesta el flujo completo.

Flujo:
  INGESTA (Rainbow/Relatorio/Tarifas/Áreas/Gerencia)
    -> CONCILIACIÓN (Rainbow <-> Personal)
    -> JORNADAS (agrupar entrada/salida, turno, HE)
    -> MATCHING TARIFARIO + VALORIZACIÓN
    -> VALIDACIÓN (estados)

Devuelve un objeto Resultado con todo lo necesario para Dashboard,
Exportación y auditoría.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import ingesta as ing
import conciliacion as cn
import reglas as rg
import tarifario as tf
import validacion as vl


class PlanError(Exception):
    """Error de configuración/ejecución del flujo."""


@dataclass
class Fuentes:
    rainbow: str | None = None
    relatorio: str | None = None
    tarifas: str | None = None
    areas: str | None = None
    gerencia: str | None = None


@dataclass
class Resultado:
    fuentes: Fuentes = field(default_factory=Fuentes)
    marcaciones: list = field(default_factory=list)
    empleados: list = field(default_factory=list)
    tarifas: list = field(default_factory=list)
    areas: list = field(default_factory=list)
    gerencias: list = field(default_factory=list)
    conciliados: list = field(default_factory=list)
    jornadas: list = field(default_factory=list)
    filas: list = field(default_factory=list)
    malformados: list = field(default_factory=list)
    avisos: list = field(default_factory=list)

    def __post_init__(self):
        self.totales = {
            "marcaciones": len(self.marcaciones),
            "empleados": len(self.empleados),
            "tarifas": len(self.tarifas),
            "conciliados": sum(1 for c in self.conciliados if c.conciliado),
            "sin_conciliar": sum(1 for c in self.conciliados if not c.conciliado),
            "jornadas": len(self.jornadas),
            "registros_detalle": len(self.filas),
        }
        self.monto_total = Decimal("0.00")
        self.horas_extra_total = Decimal("0")
        for f in self.filas:
            self.monto_total += Decimal(str(f.get("monto") or 0))
            self.horas_extra_total += Decimal(str(f.get("horas_extras") or 0))
        self.monto_total = self.monto_total.quantize(Decimal("0.01"))
        self.horas_extra_total = self.horas_extra_total.quantize(Decimal("0.0001"))
        self.estados = vl.resumen_estados(self.filas)


class MotorHorasExtrasMasiva:
    """Orquestador reutilizable (CLI, widget, web-servicio)."""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    # ------------------------------------------------------------------
    def plan(self, fuentes: Fuentes) -> Resultado:
        res = Resultado(fuentes=fuentes)

        if not fuentes.rainbow:
            raise PlanError("Falta el archivo RAINBOW (marcaciones).")
        if not fuentes.relatorio:
            raise PlanError("Falta el maestro RELATORIO de personal.")

        # INGESTA
        res.marcaciones = ing.leer_rainbow(fuentes.rainbow, self.cfg, res.avisos)
        res.empleados = ing.leer_relatorio(fuentes.relatorio, self.cfg, res.avisos)
        # TARIFAS / ÁREAS / GERENCIA vienen del motor (embebidos) si no se
        # recibe un archivo; el usuario solo aporta RAINBOW y RELATORIO.
        res.tarifas = ing.leer_tarifas(fuentes.tarifas, self.cfg, res.avisos)
        res.areas = ing.leer_areas(fuentes.areas, self.cfg, res.avisos)
        res.gerencias = ing.leer_gerencias(fuentes.gerencia, self.cfg, res.avisos)
        ing.resolver_gerencias(res.areas, res.gerencias)

        # CONCILIACIÓN
        maestro = cn.MaestroPersonal(res.empleados, self.cfg)
        res.conciliados = cn.conciliar(res.marcaciones, maestro, self.cfg, res.avisos)

        # JORNADAS
        res.jornadas, res.malformados = _agrupar_jornadas(res, self.cfg)

        # TARIFARIO + VALORIZACIÓN
        tarifario = tf.Tarifario(res.tarifas, self.cfg)
        resultado_tarifas = {}
        for j in res.jornadas:
            resultado_tarifas.setdefault(id(j.empleado), tarifario.matching(j.empleado))
        res.filas = tf.valorizar(res.jornadas, resultado_tarifas, self.cfg)

        # VALIDACIÓN
        res.filas = vl.aplicar_estados(res.filas, self.cfg)

        res.__post_init__()
        return res


def _agrupar_jornadas(res: Resultado, cfg):
    return rg.calcular_jornadas_masivo(res.conciliados, cfg, res.avisos)


def ejecutar(fuentes: Fuentes, cfg: dict) -> Resultado:
    return MotorHorasExtrasMasiva(cfg).plan(fuentes)
