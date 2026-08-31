"""Capa 4 — MATCHING TARIFARIO.

Encuentra la Tarifa aplicable a cada empleado según EMPRESA + RUC +
OBJETO DEL CONTRATO (si aplica) + CARGO, con niveles de confianza:

  - ALTA  : coincide Empresa + RUC + Cargo
  - MEDIA : coincide Empresa + Cargo (+ Contrato/Objeto si se exige)
  - BAJA  : coincide solo Cargo  -> "TARIFA AMBIGUA — REVISAR"

Si hay varias tarifas candidatas en el mismo nivel se marca como ambigua.
NIVEL NUNCA se infiere de la primera fila del Excel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

import ingesta as ing
import matching as mz
import utiles as u


@dataclass
class ResultadoTarifa:
    empleado: ing.Empleado | None = None
    tarifa: ing.Tarifa | None = None
    nivel: str = ""            # ALTA / MEDIA / BAJA / SIN_TARIFA
    cargo_match: bool = False
    ruc_match: bool = False
    empresa_match: bool = False
    objeto_match: bool = False
    ambigua: bool = False
    confianza: float = 0.0
    mensaje: str = ""


class Tarifario:
    def __init__(self, tarifas: list[ing.Tarifa], cfg):
        self.tarifas = tarifas
        self.cfg = cfg
        mt = cfg.get("matching_tarifas") or {}
        self.claves = mt.get("claves", ("ruc", "empresa", "cargo"))
        self.requiere_objeto = mt.get("requiere_objeto", False)
        self._cache_cargo: dict[str, list] = {}
        # índice por cargo normalizado
        for t in tarifas:
            k = u.normalizar_texto(t.cargo)
            self._cache_cargo.setdefault(k, []).append(t)
        self._cache_ratio: dict = {}

    # -- helpers -----------------------------------------------------------
    def _norm_empresa(self, s: str) -> str:
        return u.normalizar_texto(s)

    def _candidos_por_cargo(self, cargo: str) -> list[ing.Tarifa]:
        k = u.normalizar_texto(cargo)
        exact = self._cache_cargo.get(k, [])
        if exact:
            return list(exact)
        # difuso
        mejores: list[tuple[ing.Tarifa, float]] = []
        for tk, ts in self._cache_cargo.items():
            key = (k, tk)
            if key in self._cache_ratio:
                r = self._cache_ratio[key]
            else:
                r = mz.mejor_token(k, tk)
                self._cache_ratio[key] = r
            if r >= 70:
                for t in ts:
                    mejores.append((t, r))
        mejores.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in mejores]

    # -- matching principal -------------------------------------------------
    def matching(self, e: ing.Empleado) -> ResultadoTarifa:
        res = ResultadoTarifa(empleado=e)
        if e.cargo is None or not str(e.cargo).strip():
            res.nivel = "SIN_TARIFA"
            res.mensaje = "Empleado sin cargo"
            return res
        cargo_target = u.normalizar_texto(e.cargo)
        cands = self._candidos_por_cargo(e.cargo)
        if not cands:
            res.nivel = "SIN_TARIFA"
            res.mensaje = "Sin tarifa para el cargo '%s'" % e.cargo
            return res

        ruc_e = u.normalizar_texto(e.ruc)
        emp_e = self._norm_empresa(e.empresa_terceros or e.nombre_comercial or e.empresa)
        obj_e = u.normalizar_texto(e.contrato)

        # Nivel ALTA: RUC + Empresa + Cargo
        altas = [t for t in cands
                 if u.normalizar_texto(t.ruc) == ruc_e
                 and self._norm_empresa(t.empresa) == emp_e]
        if self.requiere_objeto:
            altas = [t for t in altas if u.normalizar_texto(t.objeto) == obj_e]
        if len(altas) == 1:
            t = altas[0]
            res.tarifa = t; res.nivel = "ALTA"; res.confianza = 100.0
            res.ruc_match = res.empresa_match = res.cargo_match = True
            res.objeto_match = (u.normalizar_texto(t.objeto) == obj_e)
            return res
        if len(altas) > 1:
            res.nivel = "ALTA"; res.ambigua = True; res.confianza = 50.0
            res.tarifa = altas[0]
            res.mensaje = "Múltiples tarifas ALTA (RUC+Empresa+Cargo) — REVISAR"
            return res

        # Nivel MEDIA: Empresa + Cargo
        medias = [t for t in cands if self._norm_empresa(t.empresa) == emp_e]
        if len(medias) == 1:
            t = medias[0]
            res.tarifa = t; res.nivel = "MEDIA"; res.confianza = 65.0
            res.empresa_match = res.cargo_match = True
            return res
        if len(medias) > 1:
            res.nivel = "MEDIA"; res.ambigua = True; res.confianza = 35.0
            res.tarifa = medias[0]
            res.mensaje = "Múltiples tarifas MEDIA (Empresa+Cargo) — REVISAR"
            return res

        # Nivel BAJA: solo Cargo -> ambigua
        res.nivel = "BAJA"; res.ambigua = True; res.confianza = 20.0
        res.cargo_match = True
        res.tarifa = cands[0]
        res.mensaje = "Tarifa por cargo únicamente — AMBIGUA, REVISAR"
        return res


def valorizar(jornadas, resultados_tarifa: dict, cfg) -> list:
    """Asigna tipo de hora (25/35/100) y tarifa y calcula monto por jornada.

    Clasificación (parametrizable en config.horas_extras.clasificacion):
    - SOBRETIEMPO: HE < 7h -> primeras 'horas_limite_25' a 25%, exceso a 35%.
    - ACTIVACION:  HE >= 7h -> 100%.
    Devuelve lista de dicts listos para la exportación.
    """
    he_cfg = cfg.get("horas_extras") or {}
    tipos = he_cfg.get("tipos_hora") or {}
    clasif = he_cfg.get("clasificacion") or {}
    resultado = []
    for j in jornadas:
        res_tarifa = resultados_tarifa.get(id(j.empleado))
        tarifa = res_tarifa.tarifa if res_tarifa else None
        extras = j.horas_extras_positivas
        fila = {
            "fecha": j.fecha,
            "empleado": j.empleado.empleado,
            "dni": j.empleado.dni,
            "fotocheck": j.empleado.fotocheck,
            "cargo": j.empleado.cargo,
            "empresa": j.empleado.empresa_terceros or j.empleado.nombre_comercial,
            "ruc": j.empleado.ruc,
            "contrato": j.empleado.contrato,
            "turno": j.turno,
            "inicio": j.inicio.strftime("%H:%M") if j.inicio else "",
            "fin": j.fin.strftime("%H:%M") if j.fin else "",
            "horas_trabajadas": j.horas_trabajadas,
            "jornada": j.jornada,
            "horas_extras": extras,
            "estado": "OK",
            "nivel_tarifa": (res_tarifa.nivel if res_tarifa else "SIN_TARIFA"),
            "confianza_tarifa": (res_tarifa.confianza if res_tarifa else 0.0),
        }
        # clasificar tipo de hora
        tipo = ""
        horas_tipo = Decimal("0")
        hay_he = extras > 0
        if hay_he and tarifa and res_tarifa and res_tarifa.nivel != "SIN_TARIFA":
            if extras >= Decimal(str(clasif.get("ACTIVACION", {}).get("min_horas_extras", 7))):
                tipo = clasif["ACTIVACION"].get("tipo_100", "100%")
                horas_tipo = extras
            else:
                limite25 = Decimal(str(clasif.get("SOBRETIEMPO", {}).get("horas_limite_25", 2)))
                h25 = min(extras, limite25)
                h35 = extras - h25
                tipo = "25%/35%"
                fila["horas_25"] = h25
                fila["horas_35"] = h35
                horas_tipo = extras
        fila["tipo_hora"] = tipo
        fila["horas_tipo"] = horas_tipo
        # tarifa y monto. Solo se marca REVISAR/ERROR cuando HAY horas extras
        # que no pudieron valorizarse por falta de tarifa.
        if hay_he and tarifa and res_tarifa and res_tarifa.nivel != "SIN_TARIFA":
            if "25%/35%" in tipo:
                t25 = tarifa.columna("25%")
                t35 = tarifa.columna("35%")
                fila["tarifa"] = t25
                monto = (fila["horas_25"] * t25 + fila["horas_35"] * t35)
                fila["monto"] = monto.quantize(Decimal("0.01"))
                fila["especifica"] = "25%%=%s h, 35%%=%s h" % (fila["horas_25"], fila["horas_35"])
            else:
                t = tarifa.columna(tipo if tipo else "100%")
                fila["tarifa"] = t
                monto = horas_tipo * t
                fila["monto"] = monto.quantize(Decimal("0.01"))
                fila["especifica"] = "%s=%s h" % (tipo, horas_tipo)
        else:
            fila["tarifa"] = Decimal("0")
            fila["monto"] = Decimal("0.00")
            if hay_he:
                if res_tarifa and res_tarifa.ambigua:
                    fila["estado"] = "REVISAR"
                elif res_tarifa and res_tarifa.nivel == "SIN_TARIFA":
                    fila["estado"] = "ERROR"
        resultado.append(fila)
    return resultado
