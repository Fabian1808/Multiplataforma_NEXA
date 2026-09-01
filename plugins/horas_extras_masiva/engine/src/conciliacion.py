"""Capa de CONCILIACIÓN: une marcaciones RAINBOW con el maestro de personal.

Estrategia:
1. Claves exactas secuenciales: DNI > Fotocheck > Num Personal.
2. Si no hay clave exacta, caer a matching por nombre normalizado (difuso
   + alias) con umbral configurable.
3. Cada marcación queda ligada a 0..1 empleado; la ausencia se registra
   como no conciliada (estado ERROR) si el horizonte lo permite.
"""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal

import ingesta as ing
import matching as mz
import utiles as u


@dataclass
class RegistroConciliado:
    marcacion: ing.Marcacion
    empleado: ing.Empleado | None = None
    metodo: str = ""          # 'dni' | 'fotocheck' | 'num_personal' | 'nombre' | 'nombre_difuso' | 'sin_conciliar'
    confianza: float = 100.0
    notas: list[str] = field(default_factory=list)

    @property
    def conciliado(self) -> bool:
        return self.empleado is not None


class MaestroPersonal:
    """Índice de empleados por múltiples claves y por nombre normalizado."""

    def __init__(self, empleados: list[ing.Empleado], cfg):
        self.empleados = empleados
        self.cfg = cfg
        self._por_dni: dict[str, list[ing.Empleado]] = defaultdict(list)
        self._por_fotocheck: dict[str, list[ing.Empleado]] = defaultdict(list)
        self._por_numpersonal: dict[str, list[ing.Empleado]] = defaultdict(list)
        self._por_nombre_norm: dict[str, ing.Empleado] = {}
        self._entradas_nombre: list = []   # (Empleado, nombre_norm, frozenset tokens)
        self._indice_token: dict = {}      # token -> [índices en _entradas_nombre]
        self._cache_ratio: dict = {}
        self._cache_nom_fuzzy: dict = {}
        self._build()

    def _norm(self, nombre: str) -> str:
        return u.normalizar_nombre(nombre, self.cfg)

    def _build(self):
        alias_cfg = (self.cfg.get("conciliacion") or {}).get("matching") or {}
        alias_on = (alias_cfg.get("alias") or {}).get("activo", True)
        self._entradas_nombre = []  # (Empleado, nombre_norm, tokens)
        indice_token: dict[str, list[int]] = defaultdict(list)
        for e in self.empleados:
            if e.dni:
                self._por_dni[e.dni].append(e)
            if e.fotocheck:
                self._por_fotocheck[e.fotocheck].append(e)
            # num personal: derivado del código del empleado '000000002 - NOMBRE'
            cod = u.limpiar_codigo(e.empleado)
            if cod and len(cod) >= 4:
                self._por_numpersonal[cod].append(e)
            nn = self._norm(e.empleado)
            if nn:
                self._por_nombre_norm[nn] = e
                toks = frozenset(nn.split())
                self._entradas_nombre.append((e, nn, toks))
                idx = len(self._entradas_nombre) - 1
                for tk in toks:
                    indice_token[tk].append(idx)
        self._indice_token = dict(indice_token)
        if alias_on:
            self._cache_ratio = {}

    # -- lookups exactos ----------------------------------------------------
    def por_dni(self, dni) -> list[ing.Empleado]:
        return self._por_dni.get(dni or "", [])

    def por_fotocheck(self, fc) -> list[ing.Empleado]:
        return self._por_fotocheck.get(fc or "", [])

    def por_numpersonal(self, np) -> list[ing.Empleado]:
        return self._por_numpersonal.get(np or "", [])

    def por_nombre_norm(self, nn) -> ing.Empleado | None:
        return self._por_nombre_norm.get(nn)

    # -- búsqueda difusa ----------------------------------------------------
    def buscar_nombre(self, nombre_original: str, umbral: float) -> list[tuple[ing.Empleado, float]]:
        nn = self._cache_nom_fuzzy.get(nombre_original)
        if nn is None:
            nn = self._norm(nombre_original)
            self._cache_nom_fuzzy[nombre_original] = nn
        if not nn:
            return []
        # exacto primero
        emp = self._por_nombre_norm.get(nn)
        if emp:
            return [(emp, 100.0)]
        # A/B temporal (FASE 3): si HEM_FUZZY_BRUTE=1 se fuerza el barrido
        # completo original para verificar equivalencia con el índice invertido.
        if os.environ.get("HEM_FUZZY_BRUTE") == "1":
            return self._buscar_nombre_bruto(nn, umbral)
        # índice invertido de tokens: solo candidatos que comparten >=1 token
        # (evita 16k comparaciones SequenceMatcher por nombre sin coincidencia).
        candidatos = set()
        for tk in nn.split():
            candidatos.update(self._indice_token.get(tk, ()))
        resultados = []
        for idx in sorted(candidatos):
            e, target, _toks = self._entradas_nombre[idx]
            key = (nn, target)
            if key in self._cache_ratio:
                r = self._cache_ratio[key]
            else:
                r = mz.mejor_token(nn, target)
                self._cache_ratio[key] = r
            if r >= umbral:
                resultados.append((e, r))
        vistos = {}
        unicos = []
        for emp_rc, r in resultados:
            if id(emp_rc) not in vistos:
                vistos[id(emp_rc)] = True
                unicos.append((emp_rc, r))
        unicos.sort(key=lambda x: x[1], reverse=True)
        return unicos[:5]

    def _buscar_nombre_bruto(self, nn: str, umbral: float):
        """Barrido original (antes de FASE 3): compara contra todos los nombres."""
        resultados = []
        for e, target, _toks in self._entradas_nombre:
            key = (nn, target)
            if key in self._cache_ratio:
                r = self._cache_ratio[key]
            else:
                r = mz.mejor_token(nn, target)
                self._cache_ratio[key] = r
            if r >= umbral:
                resultados.append((e, r))
        vistos = {}
        unicos = []
        for emp_rc, r in resultados:
            if id(emp_rc) not in vistos:
                vistos[id(emp_rc)] = True
                unicos.append((emp_rc, r))
        unicos.sort(key=lambda x: x[1], reverse=True)
        return unicos[:5]


def conciliar(marcaciones: list[ing.Marcacion], maestro: MaestroPersonal,
              cfg, avisos=None) -> list[RegistroConciliado]:
    avisos = [] if avisos is None else avisos
    cc = cfg.get("conciliacion") or {}
    claves = cc.get("claves") or {"dni"}
    umbral = (cc.get("matching") or {}).get("umbral_difusa_min", 82.0)

    registros = []
    de_conci = [("dni", maestro.por_dni, lambda m: m.dni),
                ("fotocheck", maestro.por_fotocheck, lambda m: m.fotocheck),
                ("num_personal", maestro.por_numpersonal, lambda m: m.num_personal)]
    for mar in marcaciones:
        emp = None
        metodo = "sin_conciliar"
        conf = 0.0
        # 1) claves exactas en orden de preferencia
        for nombre, fn, extraer in de_conci:
            if nombre not in claves:
                continue
            valor = extraer(mar)
            if not valor:
                continue
            matches = fn(valor)
            if len(matches) == 1:
                emp = matches[0]
                metodo = nombre
                conf = 100.0
                break
            elif len(matches) > 1:
                # múltiples personas con misma clave (baja probabilidad) -> difuso
                continue
        # 2) nombre
        if emp is None:
            cands = maestro.buscar_nombre(mar.empleado, umbral)
            if cands:
                emp, conf = cands[0]
                metodo = "nombre_difuso" if conf < 100.0 else "nombre"
                # evitar ambiguedad: si el mejor y segundo están muy juntos -> sin conciliar
                if len(cands) > 1:
                    margen = cc.get("matching", {}).get("margen_ambiguo", 2.0)
                    if (cands[0][1] - cands[1][1]) <= margen:
                        emp = None
                        metodo = "sin_conciliar_ambiguo"
        reg = RegistroConciliado(marcacion=mar, empleado=emp, metodo=metodo,
                                 confianza=conf)
        if emp is None:
            reg.notas.append("Sin emparejar en el maestro")
        registros.append(reg)
    return registros
