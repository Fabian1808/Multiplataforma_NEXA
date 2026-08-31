"""Capa DASHBOARD — agregaciones y análisis TOP.

Opera sobre resultado.filas (ya valorizadas) para producir KPIs:
  - Mayor pago / mayor monto por trabajador, cargo, empresa, área, gerencia
  - Total de horas extras y monto
  - Distribución por turno y por tipo de hora
Los resultados alimentan la vista Qt y el análisis.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal


class Analisis:
    def __init__(self, resultado):
        self.filas = resultado.filas
        self._kpis = {}
        self._tops = {}
        self._por_turno = defaultdict(lambda: {"horas": Decimal("0"), "monto": Decimal("0.00")})
        self._por_tipo = defaultdict(lambda: {"horas": Decimal("0"), "monto": Decimal("0.00")})
        self._procesar()

    def _procesar(self):
        total_h = Decimal("0")
        total_m = Decimal("0")
        agg = {  # clave -> {grupo: {horas, monto}}
            "trabajador": defaultdict(lambda: {"horas": Decimal("0"), "monto": Decimal("0.00")}),
            "cargo": defaultdict(lambda: {"horas": Decimal("0"), "monto": Decimal("0.00")}),
            "empresa": defaultdict(lambda: {"horas": Decimal("0"), "monto": Decimal("0.00")}),
            "turno": defaultdict(lambda: {"horas": Decimal("0"), "monto": Decimal("0.00")}),
        }
        for f in self.filas:
            h = Decimal(str(f.get("horas_extras") or 0))
            m = Decimal(str(f.get("monto") or 0))
            total_h += h
            total_m += m
            campos = {
                "trabajador": f.get("empleado"),
                "cargo": f.get("cargo"),
                "empresa": f.get("empresa"),
                "turno": f.get("turno"),
            }
            for dim, clave in campos.items():
                if clave:
                    agg[dim][clave]["horas"] += h
                    agg[dim][clave]["monto"] += m
            tt = f.get("tipo_hora") or "sin tipo"
            self._por_turno[f.get("turno") or "?"]["horas"] += h
            self._por_turno[f.get("turno") or "?"]["monto"] += m
            self._por_tipo[tt]["horas"] += h
            self._por_tipo[tt]["monto"] += m
        self._kpis = {
            "horas_totales": total_h.quantize(Decimal("0.0001")),
            "monto_total": total_m.quantize(Decimal("0.01")),
            "n_detalle": len(self.filas),
        }
        for dim, data in agg.items():
            top = sorted(data.items(), key=lambda kv: kv[1]["monto"], reverse=True)
            self._tops[dim] = top[:10]

    @property
    def kpis(self):
        return self._kpis

    def top(self, dim):
        return self._tops.get(dim, [])

    @property
    def por_turno(self):
        return dict(self._por_turno)

    @property
    def por_tipo(self):
        return dict(self._por_tipo)
