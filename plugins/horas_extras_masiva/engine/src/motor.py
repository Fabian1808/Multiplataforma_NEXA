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

import logging
import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import ingesta as ing
import conciliacion as cn
import reglas as rg
import tarifario as tf
import validacion as vl

logger = logging.getLogger("horas_extras_masiva.motor")


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
    def plan(self, fuentes: Fuentes, on_etapa=None) -> Resultado:
        """Ejecuta el flujo completo.

        `on_etapa` (opcional): callback(nombre: str, pct: int) invocado desde el
        hilo que llama a `plan()` para reportar el avance por fase. NO bloquea.
        """
        t_total = time.perf_counter()

        def _etapa(nombre: str, pct: int, tini: float):
            logger.info("motor etapa %-40s %3d%%  +%.2fs",
                        nombre, pct, time.perf_counter() - tini)

        res = Resultado(fuentes=fuentes)

        if not fuentes.rainbow:
            raise PlanError("Falta el archivo RAINBOW (marcaciones).")
        if not fuentes.relatorio:
            raise PlanError("Falta el maestro RELATORIO de personal.")

        # INGESTA
        t0 = t_total
        if on_etapa:
            on_etapa("Leyendo marcaciones RAINBOW", 5)
        res.marcaciones = ing.leer_rainbow(fuentes.rainbow, self.cfg, res.avisos)
        _etapa("rainbow", 5, t0)
        t0 = time.perf_counter()
        if on_etapa:
            on_etapa("Leyendo maestro RELATORIO", 18)
        res.empleados = ing.leer_relatorio(fuentes.relatorio, self.cfg, res.avisos)
        _etapa("relatorio", 18, t0)
        t0 = time.perf_counter()
        if on_etapa:
            on_etapa("Tarifas / Áreas / Gerencia", 22)
        res.tarifas = ing.leer_tarifas(fuentes.tarifas, self.cfg, res.avisos)
        res.areas = ing.leer_areas(fuentes.areas, self.cfg, res.avisos)
        res.gerencias = ing.leer_gerencias(fuentes.gerencia, self.cfg, res.avisos)
        ing.resolver_gerencias(res.areas, res.gerencias)
        _etapa("tar/areas/ger", 22, t0)

        # CONCILIACIÓN
        t0 = time.perf_counter()
        if on_etapa:
            on_etapa("Conciliando marcaciones con personal", 30)
        maestro = cn.MaestroPersonal(res.empleados, self.cfg)
        res.conciliados = cn.conciliar(res.marcaciones, maestro, self.cfg, res.avisos)
        _etapa("conciliacion", 30, t0)

        # JORNADAS
        t0 = time.perf_counter()
        if on_etapa:
            on_etapa("Armando jornadas laborales", 75)
        res.jornadas, res.malformados = _agrupar_jornadas(res, self.cfg)
        _etapa("jornadas", 75, t0)

        # TARIFARIO + VALORIZACIÓN
        t0 = time.perf_counter()
        if on_etapa:
            on_etapa("Matching tarifario y valorización", 87)
        tarifario = tf.Tarifario(res.tarifas, self.cfg)
        resultado_tarifas = {}
        for j in res.jornadas:
            resultado_tarifas.setdefault(id(j.empleado), tarifario.matching(j.empleado))
        res.filas = tf.valorizar(res.jornadas, resultado_tarifas, self.cfg)
        _etapa("tarifario", 87, t0)

        # VALIDACIÓN
        t0 = time.perf_counter()
        if on_etapa:
            on_etapa("Validando estados", 97)
        res.filas = vl.aplicar_estados(res.filas, self.cfg)
        _etapa("estados", 97, t0)

        res.__post_init__()
        logger.info("motor completo en %.2fs (jornadas=%d)",
                    time.perf_counter() - t_total, res.totales["jornadas"])
        if on_etapa:
            on_etapa("Completado", 100)
        return res


def _agrupar_jornadas(res: Resultado, cfg):
    return rg.calcular_jornadas_masivo(res.conciliados, cfg, res.avisos)


def ejecutar(fuentes: Fuentes, cfg: dict, on_etapa=None) -> Resultado:
    return MotorHorasExtrasMasiva(cfg).plan(fuentes, on_etapa=on_etapa)
