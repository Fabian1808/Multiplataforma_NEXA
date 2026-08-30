"""Punto de entrada del sistema.

Flujo:
  1. Cargar configuración (config/config.json).
  2. Leer consolidado y relatorio(s).
  3. Conciliar cada registro (matching + marcaciones + turno).
  4. Validar (estado y confianza).
  5. Calcular impacto económico.
  6. Exportar log, histórico y (si no es modo prueba) consolidado completado.

Ejecución CLI:
    python src/main.py --config config/config.json

También se usa desde la interfaz gráfica en el MISMO proceso
(ejecutar_para_gui), lo que elimina el subproceso y facilita el
empaquetado como ejecutable.
"""

import argparse
import io
import json
import os
import sys
import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path

if getattr(sys, "_MEIPASS", None):          # empaquetado con PyInstaller
    ROOT = Path(sys._MEIPASS)
else:
    ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import config as cfg_mod
import lectura
from conciliacion import conciliar, indexar_marcaciones
from exportacion import ESTADOS_HE_REVISION, ETIQUETA_REVISION, \
    _horas_extras_fmt, generar_historico, generar_log, escribir_consolidado, \
    verificar_escritura
from impacto import calcular_impacto, calcular_productividad
from matching import construir_indice
from validacion import validar_respuesta
from agregacion import construir_dashboard

MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
         "JULIO", "AGOSTO", "SETIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]


def _periodo_nombre(fechas):
    """El periodo se determina por el mes con más registros (modo)."""
    contador = Counter((f.month, f.year) for f in fechas)
    (mes, anio), _n = contador.most_common(1)[0]
    return "%02d_%s_%d" % (mes, MESES[mes - 1], anio)


def _cargar_argumentos():
    parser = argparse.ArgumentParser(description="Sistema de validación de horas extras")
    parser.add_argument("--config", default=None, help="Ruta a config.json")
    parser.add_argument("--consolidado", default=None, help="Ruta al consolidado (sobreescribe config)")
    parser.add_argument("--relatorio", nargs="+", default=None, help="Rutas a relatorio(s) de marcaciones")
    parser.add_argument("--modo-prueba", dest="modo_prueba", action="store_true", default=None,
                        help="Fuerza modo prueba (True/Falso según flag)")
    parser.add_argument("--empresa", default=None, help="Empresa contratista a procesar (sobreescribe config)")
    return parser.parse_args()


def _resolver_rutas(args, cfg):
    if args.consolidado:
        cfg["rutas"]["input_consolidado"] = args.consolidado
    if args.relatorio:
        cfg["rutas"]["input_relatorio"] = args.relatorio
    rel = cfg["rutas"].get("input_relatorio") or []
    if isinstance(rel, str):
        rel = [rel]
    cfg["rutas"]["input_relatorio"] = rel
    for clave in ("output_dir", "historicos_dir", "logs_dir"):
        os.makedirs(Path(cfg["rutas"][clave]).resolve(), exist_ok=True)


def _filtrar_marcas_por_empresa(marcaciones, cfg, avisos):
    """Conserva solo las marcas de la empresa activa (si el relatorio trae
    varias empresas en la columna 'Empresa Tercero')."""
    if not cfg.get("empresas"):
        return marcaciones
    activa = cfg["empresa_info"]["nombre"]
    conservadas = []
    omitidas = 0
    for m in marcaciones:
        if m.get("empresa_raw") is None:
            conservadas.append(m)
        elif m.get("empresa") == activa:
            conservadas.append(m)
        else:
            omitidas += 1
    if omitidas:
        avisos.append("Relatorio: %d marca(s) de otras empresas omitidas (empresa activa: %s)."
                      % (omitidas, activa))
    return conservadas


def _procesar(cfg):
    inicio = time.time()

    ruta_consolidado = cfg["rutas"]["input_consolidado"]

    # Abrir el consolidado UNA sola vez y reutilizarlo en la lectura,
    # la tabla de costos y (si aplica) las columnas de validación, para
    # no abrir 3 veces un archivo grande.
    libro_consolidado = None
    import openpyxl as _ox
    try:
        libro_consolidado = _ox.load_workbook(ruta_consolidado, data_only=True)
    except Exception:
        libro_consolidado = None

    try:
        registros = lectura.leer_consolidado(
            ruta_consolidado, cfg, [], wb=libro_consolidado)

        # Cargar tabla de costos de HHEE desde el consolidado
        tabla_costos = lectura.cargar_tabla_costos(
            ruta_consolidado, wb=libro_consolidado)
        cfg["_tabla_costos"] = tabla_costos
    except Exception:
        if libro_consolidado is not None:
            try:
                libro_consolidado.close()
            except Exception:
                pass
        raise

    avisos = []
    marcaciones, avisos = lectura.leer_relatorio(cfg["rutas"]["input_relatorio"], cfg, avisos)
    marcaciones = _filtrar_marcas_por_empresa(marcaciones, cfg, avisos)

    identidades = construir_indice(marcaciones)
    indice_marcas = indexar_marcaciones(
        marcaciones, cfg["marcaciones"]["incluir_denegados"],
        dedupe_segundos=cfg["marcaciones"].get("dedupe_segundos", 60),
        dedupe_estrategia=cfg["marcaciones"].get(
            "dedupe_estrategia", "entrada_primera_salida_ultima"))
    cfg["_match_cache"] = {}  # memo del matching difuso entre registros

    resultados = []
    for reg in registros:
        res = validar_respuesta(
            conciliar(reg, marcaciones, indice_marcas, identidades, cfg), cfg)
        resultados.append(res)

    tiempo_ejecucion = time.time() - inicio
    productividad = calcular_productividad(resultados, cfg, tiempo_ejecucion)
    impacto = calcular_impacto(resultados)
    dashboard = construir_dashboard(resultados)
    periodo = _periodo_nombre([r.fecha for r in resultados])

    log_ruta = generar_log(resultados, cfg["rutas"]["logs_dir"], periodo)
    carpeta_historico = generar_historico(
        resultados, productividad, impacto, cfg, periodo,
        fecha_ejecucion=datetime.now(), log_ruta=log_ruta, dashboard=dashboard)

    mensajes = {"log": log_ruta, "historico": carpeta_historico}
    if not cfg["modo_prueba"]:
        ruta_consolidado = escribir_consolidado(
            cfg["rutas"]["input_consolidado"], registros, resultados, cfg, periodo)
        mensajes["consolidado"] = ruta_consolidado
        mensajes["verificacion"] = verificar_escritura(
            ruta_consolidado, registros, resultados, cfg)

    if libro_consolidado is not None:
        try:
            libro_consolidado.close()
        except Exception:
            pass

    return resultados, productividad, impacto, periodo, mensajes, tiempo_ejecucion, avisos


def _resumen(resultados, productividad, impacto, periodo, mensajes, cfg, avisos=None):
    estados = Counter(r.estado for r in resultados)
    confianza = Counter(r.confianza for r in resultados)
    turnos = Counter(r.turno for r in resultados)

    he_min = sum(int(round(r.horas_extras * 60)) for r in resultados
                 if r.horas_extras is not None
                 and r.estado not in ESTADOS_HE_REVISION)
    n_revision = sum(1 for r in resultados
                     if _horas_extras_fmt(r) == ETIQUETA_REVISION)

    print("=" * 64)
    print("CONTROL DE HORAS EXTRAS  |  Periodo: %s  |  Empresa: %s"
          % (periodo, cfg["empresa_info"]["nombre"]))
    print("=" * 64)
    print("Registros procesados: %d  |  Turnos: %s" % (len(resultados), dict(turnos)))
    print("Estados: %s" % dict(estados))
    print("Confianza: %s" % dict(confianza))
    print("Horas extras calculadas: %d:%02d h  |  %s: %d registro(s)"
          % (he_min // 60, he_min % 60, ETIQUETA_REVISION, n_revision))
    print("-" * 64)
    if "consolidado" in mensajes:
        print("EXCEL COMPLETADO LISTO: %s" % mensajes["consolidado"])
        print("  El archivo conserva TODAS las columnas del original y agrega:")
        print("  AZ (Entrada) | BA (Salida) | BE (Comentario) | BC/BD (Liquidacion)")
        print("  AD/AE/AF (Horas 25%/35%/100%) | AI/AJ/AK (Costo HHEE)")
        print("  AL (Total HHEE) | AM-AO (Movilidad) | AP (Alim.) | AQ (Total)")
        verif = mensajes.get("verificacion")
        if verif:
            if "error" in verif:
                print("  VERIFICACION: %s" % verif["error"])
            else:
                partes = ["%s %d/%d" % (c.replace(" ", "-"), verif["escritas"][c],
                                        verif["esperadas"][c])
                          for c in verif["esperadas"]]
                if verif["faltantes"]:
                    print("  VERIFICACION [INCOMPLETA, %d celda(s) faltante(s)]: %s"
                          % (verif["total_faltantes"], " | ".join(partes)))
                else:
                    print("  VERIFICACION [OK]: %s" % " | ".join(partes))
        print("-" * 64)
    print("B. IMPACTO ECONOMICO")
    mono = cfg["impacto"]["moneda"]
    print("  Monto declarado:   %s%.2f" % (mono, impacto["monto_declarado"]))
    print("  Monto validado:    %s%.2f" % (mono, impacto["monto_validado"]))
    print("  Monto observado:   %s%.2f" % (mono, impacto["monto_observado"]))
    print("  Monto pendiente:   %s%.2f" % (mono, impacto["monto_pendiente"]))
    print("  Ahorro potencial:  %s%.2f  |  Confirmado: %s%.2f  |  Reducción: %.1f %%" % (
        mono, impacto["ahorro_potencial"], mono, impacto["ahorro_confirmado"], impacto["reduccion_pct"]))
    print("-" * 64)
    print("Archivos generados:")
    for clave, ruta in mensajes.items():
        if clave == "verificacion":
            continue
        print("  %-12s %s" % (clave + ":", ruta))
    if avisos:
        print("-" * 64)
        print("Avisos de lectura (%d):" % len(avisos))
        for a in avisos:
            print("  ! %s" % a)


def main():
    args = _cargar_argumentos()
    cfg = cfg_mod.cargar_config(args.config)
    if args.empresa:
        cfg = cfg_mod.aplicar_empresa(cfg, args.empresa)
    if args.modo_prueba is not None:
        cfg["modo_prueba"] = args.modo_prueba
    _resolver_rutas(args, cfg)

    resultados, productividad, impacto, periodo, mensajes, _t, avisos = _procesar(cfg)
    _resumen(resultados, productividad, impacto, periodo, mensajes, cfg, avisos)
    if "consolidado" in mensajes:
        print("\n[OK] Consolidado completado generado. El archivo original no fue modificado.")


def _dir_logs_interno():
    """Carpeta de logs interna de la app (donde vive el .exe, o %APPDATA%)."""
    if getattr(sys, "_MEIPASS", None):
        return str(Path(os.environ.get("APPDATA", str(Path.home()))) /
                   "NEXA" / "HorasExtras" / "logs")
    return str(ROOT / "logs")


def ejecutar_para_gui(config_ruta, empresa=None, consolidado=None, relatorios=None):
    """Ejecuta el proceso completo y devuelve (salida_texto, exito).

    Pensada para la interfaz gráfica: captura la salida en memoria y convierte
    cualquier excepción en un mensaje amigable (nunca propaga la excepción, para
    que la aplicación no se cierre inesperadamente).
    """
    salida = io.StringIO()
    out_orig, err_orig = sys.stdout, sys.stderr
    exito = False
    try:
        sys.stdout = salida
        sys.stderr = salida
        cfg = cfg_mod.cargar_config(config_ruta)
        if empresa:
            cfg = cfg_mod.aplicar_empresa(cfg, empresa)
            
        # El GUI siempre espera generar el Excel, forzamos false.
        cfg["modo_prueba"] = False
            
        if consolidado:
            cfg["rutas"]["input_consolidado"] = consolidado
        if relatorios:
            cfg["rutas"]["input_relatorio"] = relatorios

        rel = cfg["rutas"].get("input_relatorio") or []
        if isinstance(rel, str):
            rel = [rel]
        cfg["rutas"]["input_relatorio"] = rel
        for clave in ("output_dir", "historicos_dir", "logs_dir"):
            try:
                os.makedirs(Path(cfg["rutas"][clave]).resolve(), exist_ok=True)
            except Exception as exc:
                print("AVISO: no se pudo crear la carpeta %s (%s)" % (clave, exc))

        resultados, productividad, impacto, periodo, mensajes, _t, avisos = _procesar(cfg)
        _resumen(resultados, productividad, impacto, periodo, mensajes, cfg, avisos)
        if "consolidado" in mensajes:
            print("\n[OK] Consolidado completado generado. El archivo original no fue modificado.")
        try:
            import tempfile
            dash_path = os.path.join(tempfile.gettempdir(),
                                     "nexa_dashboard_%d.json" % os.getpid())
            dashboard_data = construir_dashboard(resultados)
            dash_payload = {"dashboard": dashboard_data, "resultados": [
                {"empleado": r.empleado, "fecha": str(r.fecha), "turno": r.turno,
                 "horas_extras": r.horas_extras, "costo_total": getattr(r, "costo_total", 0),
                 "estado": r.estado, "confianza": r.confianza,
                 "especialidad": getattr(r, "especialidad", ""),
                 "horas_25": getattr(r, "horas_25", 0), "horas_35": getattr(r, "horas_35", 0),
                 "horas_100": getattr(r, "horas_100", 0), "valor_hhee": getattr(r, "valor_hhee", 0),
                 "monto_total": getattr(r, "monto_total", 0),
                 "validacion_rainbow": getattr(r, "validacion_rainbow", ""),
                 "tipo_rev": getattr(r, "tipo_rev", ""),
                 "dni": getattr(r, "dni", ""),
                 "transporte_valor": getattr(r, "transporte_valor", 0),
                 "alimentacion_valor": getattr(r, "alimentacion_valor", 0),
                 } for r in resultados], "impacto": impacto}
            with open(dash_path, "w", encoding="utf-8") as fh:
                json.dump(dash_payload, fh, ensure_ascii=False, indent=2, default=str)
        except Exception:
            pass
        exito = True
    except Exception as exc:
        exito = False
        print("ERROR: %s" % _mensaje_amigable(exc, config_ruta))
        try:
            ruta_log = os.path.join(_dir_logs_interno(), "error_motor.log")
            os.makedirs(os.path.dirname(ruta_log), exist_ok=True)
            with open(ruta_log, "a", encoding="utf-8") as fh:
                fh.write("%s\n%s\n" % (datetime.now().isoformat(),
                                       _sanitizar_traceback(traceback.format_exc())))
        except Exception:
            pass
    finally:
        sys.stdout, sys.stderr = out_orig, err_orig
    return salida.getvalue(), exito


def _sanitizar_traceback(texto):
    """Reemplaza rutas locales de desarrollo por marcadores genéricos.

    Evita filtrar el nombre de usuario o la ruta del proyecto en logs que
    pueden compartirse con soporte (v0.4.4).
    """
    texto = texto.replace(str(ROOT), "<PROYECTO>")
    texto = texto.replace(str(Path.home()), "<USUARIO>")
    texto = texto.replace("C:\\", "<DISCO>\\")
    texto = texto.replace("C:/", "<DISCO>/")
    return texto


def _mensaje_amigable(exc, config_ruta):
    """Traduce errores técnicos a mensajes comprensibles, conservando el resto."""
    texto = str(exc)
    bajo = texto.lower()
    # Mensajes ya amigables del propio motor (lectura/exportación): se pasan tal cual
    prefijos = ("no se encontro ", "el relatorio ", "el consolidado ", "relatorio no encontrado",
                "consolidado no encontrado", "no se pudo abrir ", "la hoja ",
                "no se pudo preparar", "tabla '")
    if texto.strip().startswith(prefijos) or bajo.strip().startswith(prefijos):
        return texto
    if "filenotfound" in bajo or "no such file" in bajo or "no existe" in bajo:
        return ("No se pudo encontrar un archivo. Verifica que exista y que la ruta "
                "sea correcta, luego inténtalo nuevamente.")
    if "permission" in bajo or "denegado" in bajo or "access" in bajo:
        return ("Sin permisos para leer/escribir el archivo o carpeta. Cierra otros "
                "programas que lo estén usando (por ejemplo Excel) e inténtalo de nuevo.")
    if "sheet" in bajo or "tabla" in bajo or "workbook" in bajo or "openpyxl" in bajo:
        return ("El archivo Excel no tiene el formato esperado o está dañado. Verifica "
                "que sea un Excel válido y que contenga la hoja '4 BDHHEE' con la tabla "
                "'Tabla3'.")
    if "not a zip" in bajo or "badzipfile" in bajo or "bad zip" in bajo:
        return ("El archivo no es un Excel válido o está dañado. Verifica que sea un "
                "archivo .xlsx real (no un archivo renombrado) y vuelve a cargarlo.")
    if "closed workbook" in bajo or "locked" in bajo:
        return "El archivo está siendo usado por otro programa (normalmente Excel). Ciérralo e inténtalo de nuevo."
    return ("Ocurrió un problema al procesar los datos (%s). Si el problema persiste, "
            "revisa el historial de errores de la aplicación." % texto[:160])


if __name__ == "__main__":
    main()