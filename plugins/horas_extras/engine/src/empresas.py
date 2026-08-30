"""Configuración dinámica por empresa contratista.

Cada empresa declara turnos en forma NOMINAL (inicio/fin) y el sistema
deriva las ventanas de entrada/salida con una tolerancia configurable.
El motor de conciliación nunca debe conocer nombres de empresa hardcodeados:
recibe turnos ya resueltos con la misma forma que la config histórica,
más la bandera `cruza_medianoche` para turnos que terminan al día siguiente.

También resuelve el nombre de la empresa desde la columna "Empresa Tercero"
de RAINBOW (ej. "0153 - CONFIPETROL / CJM" -> CONFIPETROL).
"""

import re

from config import hora_a_minutos  # config importa empresas de forma perezosa (sin ciclo)
from normalizacion import normalizar_nombre, tokens


TURNOS_ESPERADOS = ("T1", "T2", "T3")


def _hhmm(minutos):
    """Convierte minutos desde media noche a 'HH:MM' (recortado a 00:00-23:59)."""
    minutos = max(0, min(1439, int(minutos)))
    return "%02d:%02d" % divmod(minutos, 60)


def derivar_turno(tcfg, tol_entrada=None, tol_salida=None):
    """Convierte un turno nominal {inicio, fin} a ventanas del motor.

    - Sin cruce de medianoche: entrada [inicio-tol, inicio+tol] y salida
      [fin-tol, fin+tol] del día declarado.
    - Con cruce (fin < inicio): ventanas dobles (día D y D+1) y las
      heurísticas de jornada nocturna (duración, madrugada, puntaje).
    """
    cruza = tcfg.get("cruza_medianoche")
    if cruza is None:
        cruza = hora_a_minutos(tcfg["fin"]) < hora_a_minutos(tcfg["inicio"])

    tol_ent = int(tol_entrada if tol_entrada is not None else tcfg.get("tolerancia_entrada", 20))
    tol_sal = int(tol_salida if tol_salida is not None else tcfg.get("tolerancia_salida", 60))
    inicio = hora_a_minutos(tcfg["inicio"])
    fin = hora_a_minutos(tcfg["fin"])

    turno = {"cruza_medianoche": bool(cruza)}
    if not cruza:
        turno["entrada"] = {"min": _hhmm(inicio - tol_ent), "max": _hhmm(inicio + tol_ent)}
        turno["salida"] = {"min": _hhmm(fin - tol_sal), "max": _hhmm(fin + tol_sal)}
        nominal = (fin - inicio) / 60.0
        turno["rango_duracion_horas"] = [round(nominal - 3, 1), round(nominal + 3, 1)]
        return turno

    turno["entrada_dia_d"] = {"min": _hhmm(inicio - tol_ent), "max": "23:59"}
    turno["entrada_dia_dmas1"] = {"min": "00:00", "max": _hhmm(fin + tol_sal)}
    turno["salida_dia_dmas1"] = {"min": "00:00", "max": _hhmm(fin + tol_sal)}
    turno["salida_mismo_dia"] = {"min": _hhmm(inicio), "max": "23:59"}
    turno["ventana_busqueda_horas"] = 19
    nominal = (1440 - inicio + fin) / 60.0
    turno["rango_duracion_horas"] = [round(nominal - 3, 1), round(nominal + 3, 1)]
    turno["rango_duracion_madrugada_horas"] = [0.5, 8]
    turno["madrugada_horas"] = {"min": _hhmm(fin - 120), "max": _hhmm(fin + tol_sal)}
    turno["pausa_nueva_jornada_min"] = 60
    turno["puntaje_minimo"] = 55
    return turno


def validar_empresa(nombre, ecfg):
    """Valida la estructura de config de una empresa y lanza ValueError claro."""
    if not isinstance(ecfg, dict):
        raise ValueError("Empresa '%s': configuracion invalida (se esperaba un objeto)." % nombre)
    turnos = ecfg.get("turnos")
    if not isinstance(turnos, dict) or not turnos:
        raise ValueError("Empresa '%s': falta la seccion 'turnos'." % nombre)
    for t in TURNOS_ESPERADOS:
        tcfg = turnos.get(t)
        if not isinstance(tcfg, dict):
            raise ValueError("Empresa '%s': falta el turno %s en 'turnos'." % (nombre, t))
        for k in ("inicio", "fin"):
            if k not in tcfg:
                raise ValueError("Empresa '%s': el turno %s debe definir '%s'." % (nombre, t, k))
            try:
                hora_a_minutos(tcfg[k])
            except ValueError as exc:
                raise ValueError("Empresa '%s': el turno %s tiene '%s' invalido (%s)."
                                 % (nombre, t, k, exc))
        try:
            derivar_turno(tcfg)
        except (ValueError, KeyError) as exc:
            raise ValueError("Empresa '%s': el turno %s es invalido (%s)." % (nombre, t, exc))
    sobretiempo = ecfg.get("sobretiempo_maximo")
    if sobretiempo is not None:
        try:
            float(sobretiempo)
        except (TypeError, ValueError):
            raise ValueError("Empresa '%s': 'sobretiempo_maximo' debe ser un numero." % nombre)


def extraer_nombre_empresa(raw):
    """Limpia la columna 'Empresa Tercero' de RAINBOW.

    Quita el código numérico inicial y devuelve la parte nominal
    ("0153 - CONFIPETROL / CJM" -> "CONFIPETROL / CJM").
    """
    s = str(raw or "").strip()
    if not s:
        return ""
    partes = re.split(r"\s*-\s*", s)
    con_letras = [p for p in partes if re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", p)]
    if con_letras:
        s = " - ".join(con_letras)
    m = re.match(r"^\(?\d{2,4}\)?[\s/:]*", s)
    if m:
        s = s[m.end():].strip()
    return s


def _conjunto_tokens_empresa(ecfg):
    """Conjuntos de tokens normalizados de la empresa (nombre + aliases)."""
    conjuntos = []
    nombres = [str(ecfg.get("nombre") or "").strip()]
    nombres += [str(a).strip() for a in ecfg.get("aliases", [])]
    for n in nombres:
        ts = tokens(normalizar_nombre(n))
        if ts:
            conjuntos.append(ts)
    return conjuntos


def coincidir_empresa(nombre_limpio, empresas_cfg, avisos=None):
    """Devuelve el nombre canónico de empresa que coincide con `nombre_limpio`.

    Regla: el conjunto de tokens de la empresa (o de alguno de sus alias)
    debe estar contenido en el nombre leído. Si ninguna o varias empresas
    coinciden, devuelve None y registra un aviso (nunca elige al azar).
    """
    avisos = [] if avisos is None else avisos
    R = tokens(normalizar_nombre(nombre_limpio))
    if not R:
        return None
    candidatos = []
    for nombre, ecfg in empresas_cfg.items():
        for cs in _conjunto_tokens_empresa(ecfg):
            if cs <= R:
                candidatos.append(nombre)
                break
    unicos = sorted(set(candidatos))
    if len(unicos) == 1:
        return unicos[0]
    if len(unicos) > 1:
        avisos.append("Empresa Tercero %r coincide con varias empresas (%s); se omite la marca."
                      % (nombre_limpio, ", ".join(unicos)))
        return None
    avisos.append("Empresa Tercero %r no corresponde a ninguna empresa configurada; se omite la marca."
                  % nombre_limpio)
    return None


def horas_trabajadas(entrada_dt, salida_dt):
    """Horas transcurridas entre entrada y salida (0.0 si no hay jornada válida)."""
    if not entrada_dt or not salida_dt or salida_dt <= entrada_dt:
        return 0.0
    return round((salida_dt - entrada_dt).total_seconds() / 3600.0, 4)


def jornada_nominal_horas(tcfg):
    """Duración nominal del turno según la config de la empresa (en horas).

    Respeta el cruce de medianoche: T2 19:00->07:00 dura 12 h aunque fin < inicio.
    """
    inicio = hora_a_minutos(tcfg["inicio"])
    fin = hora_a_minutos(tcfg["fin"])
    if bool(tcfg.get("cruza_medianoche")) or fin <= inicio:
        return round((1440 - inicio + fin) / 60.0, 4)
    return round((fin - inicio) / 60.0, 4)


def calcular_horas_extras(horas_trabajadas_h, tcfg, ecfg=None):
    """Horas extras automáticas del turno: trabajadas - jornada nominal.

    Reglas de negocio:
    - Nunca negativas: si la jornada quedó por debajo de lo nominal -> 0.0.
    - Tope de pago: si la empresa define ``sobretiempo_maximo`` (ej. 1.5),
      las horas extras pagables quedan limitadas a ese valor; el excedente
      se informa aparte (``exceso_sobre_tope``) para revisión del negocio.
    Devuelve dict {brutas, pagables, exceso_sobre_tope} en horas decimales.
    """
    nominal = jornada_nominal_horas(tcfg)
    brutas = round(max(0.0, float(horas_trabajadas_h or 0.0) - nominal), 4)
    tope = (ecfg or {}).get("sobretiempo_maximo")
    pagables, exceso = brutas, 0.0
    if tope is not None:
        try:
            tope = float(tope)
        except (TypeError, ValueError):
            tope = None
    if tope is not None and brutas > tope:
        pagables = round(tope, 4)
        exceso = round(brutas - tope, 4)
    return {"brutas": brutas, "pagables": pagables, "exceso_sobre_tope": exceso}


def minutos_a_hhmm(minutos):
    """Minutos enteros a 'HH:MM' ('00:00' para None/0/negativos)."""
    try:
        minutos = int(round(float(minutos or 0)))
    except (TypeError, ValueError):
        return "00:00"
    return "%02d:%02d" % divmod(max(0, minutos), 60)


def horas_a_hhmm(horas):
    """Horas decimales a 'HH:MM' ('01:30' para 1.5)."""
    try:
        minutos = float(horas or 0) * 60.0
    except (TypeError, ValueError):
        return "00:00"
    return minutos_a_hhmm(minutos)


def horas_netas(horas, descuento=1.0):
    """Horas trabajadas menos el descuento de comida (nunca negativas)."""
    if horas is None or horas <= 0:
        return 0.0
    return round(max(0.0, horas - float(descuento)), 4)


def clasificar_tipo_hhee(horas, cfg=None):
    """Clasifica la duración de la jornada en tipo de HHEE.

    Rangos configurables en ``clasificacion_hhee`` (por defecto):
    - hasta ``sobretiempo_max_horas`` (3.0) -> "Sobretiempo"
    - entre ``activacion_min_horas`` (7.0) y ``activacion_max_horas`` (12.0) -> "Activación"
    - cualquier otro valor ambiguo (3-7, >12) -> "Revisar en Rainbow"
    Devuelve None si no hay horas para clasificar.
    """
    if horas is None:
        return None
    c = (cfg or {}).get("clasificacion_hhee", {})
    sobretiempo_max = float(c.get("sobretiempo_max_horas", 3.0))
    activacion_min = float(c.get("activacion_min_horas", 7.0))
    activacion_max = float(c.get("activacion_max_horas", 12.0))
    if horas <= sobretiempo_max:
        return c.get("sobretiempo", "Sobretiempo")
    if activacion_min <= horas <= activacion_max:
        return c.get("activacion", "Activación")
    return c.get("revisar", "Revisar en Rainbow")


def split_porcentajes(horas_extras, tipo, hexagesimal=None):
    """Divide las horas entre 25%, 35% y 100% según el tipo de HHEE.

    SOBRETIEMPO: primeras 2h al 25%, excedente al 35%.
    ACTIVACION: todo al 100% (usa hexagesimal = jornada neta).

    Devuelve dict {h25, h35, h100}.
    """
    tipo_upper = str(tipo or "").strip().upper()
    if "ACTIVACION" in tipo_upper:
        h = max(0.0, float(hexagesimal or 0))
        return {"h25": 0.0, "h35": 0.0, "h100": round(h, 4)}

    h = max(0.0, float(horas_extras or 0))
    h25 = round(min(h, 2.0), 4)
    h35 = round(max(h - 2.0, 0.0), 4)
    return {"h25": h25, "h35": h35, "h100": 0.0}