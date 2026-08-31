"""CLI de HORAS EXTRAS MASIVA.

Uso:
  python src/main.py --rainbow <xlsx> --relatorio <xlsx> [--tarifas <xlsx>] \
      [--areas <xlsx>] [--gerencia <xlsx>] [--config config.json] [-o salida.xlsx]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# permitir ejecutar desde dentro de engine/src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config as cfg_mod
import motor as motor_mod


def main(argv=None):
    p = argparse.ArgumentParser(description="Horas Extras Masiva (Rainbow + Relatorio + Tarifas)")
    p.add_argument("--rainbow", required=True, help="Excel de marcaciones RAINBOW")
    p.add_argument("--relatorio", required=True, help="Excel maestro de personal")
    p.add_argument("--tarifas", help="Excel de tarifas")
    p.add_argument("--areas", help="Excel de áreas (opcional)")
    p.add_argument("--gerencia", help="Excel de gerencias (opcional)")
    p.add_argument("--config", help="config.json opcional")
    p.add_argument("-o", "--output", default=None, help="Ruta del Excel de salida")
    p.add_argument("--excel-solo", action="store_true", help="Solo exportar (sin resumen en consola)")
    args = p.parse_args(argv)

    cfg = cfg_mod.cargar_config(args.config)
    fuentes = motor_mod.Fuentes(
        rainbow=args.rainbow,
        relatorio=args.relatorio,
        tarifas=args.tarifas,
        areas=args.areas,
        gerencia=args.gerencia,
    )
    resultado = motor_mod.ejecutar(fuentes, cfg)
    print("Marcaciones:", resultado.totales["marcaciones"])
    print("Personal:", resultado.totales["empleados"])
    print("Conciliados:", resultado.totales["conciliados"], "/ Sin conciliar:", resultado.totales["sin_conciliar"])
    print("Jornadas:", resultado.totales["jornadas"])
    print("Horas extras totales:", resultado.horas_extra_total)
    print("Monto total:", resultado.monto_total)
    print("Estados:", resultado.estados)

    if not args.excel_solo:
        import dashboard
        an = dashboard.Analisis(resultado)
        print("\nTop trabajadores por monto:")
        for nombre, v in an.top("trabajador"):
            print("  %s -> %s h / %s" % (nombre, v["horas"], v["monto"]))
        print("\nTop cargos por monto:")
        for nombre, v in an.top("cargo"):
            print("  %s -> %s h / %s" % (nombre, v["horas"], v["monto"]))
        print("\nPor turno:", dict((k, str(v["monto"])) for k, v in an.por_turno.items()))

    if args.output:
        import exportacion
        ruta = exportacion.exportar(resultado, args.output, cfg)
        print("\nExcel generado:", ruta)
    return resultado


if __name__ == "__main__":
    main()
