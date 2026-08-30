"""Motor de conciliación: busca marcaciones reales y determina la jornada.

Interpreta el turno declarado (T1/T2/T3), encuentra entrada y salida dentro
de ventanas derivadas de patrones reales, y entrega la evidencia para que
el módulo de validación asigne estado y confianza.
"""

import datetime
from collections import defaultdict

from config import hora_a_minutos
from empresas import calcular_horas_extras, clasificar_tipo_hhee, horas_netas, \
    horas_trabajadas, jornada_nominal_horas, split_porcentajes
from matching import construir_indice, match_empleado
from normalizacion import normalizar_nombre_cached


def _a_minutos(t):
    return t.hour * 60 + t.minute


def _to_int(valor):
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return 0


def _en_ventana(t, rango):
    return rango[0] <= _a_minutos(t) <= rango[1] if rango else True


def _rango(dict_rango):
    if not dict_rango:
        return None
    return (hora_a_minutos(dict_rango["min"]), hora_a_minutos(dict_rango["max"]))


def _a_segundos(t):
    return t.hour * 3600 + t.minute * 60 + t.second


def _dedupe_por_tipo(lista, segundos, mantener_ultima):
    """Comprime una ráfaga del mismo tipo de marcación.

    Conserva la primera de cada ráfaga para Entrada y la última para
    Salida (la persona usa la última marca de la ráfaga de salida,
    incluso si es Denegado — regla v0.2.0).
    """
    lista.sort(key=lambda m: m["hora"])
    conservadas = []
    ultima_hora_seg = None
    for m in lista:
        seg = _a_segundos(m["hora"])
        if conservadas and ultima_hora_seg is not None and (seg - ultima_hora_seg) <= segundos:
            if mantener_ultima:
                conservadas[-1] = m
            ultima_hora_seg = seg
        else:
            conservadas.append(m)
            ultima_hora_seg = seg
    return conservadas


def _dedupe_grupo(grupo, segundos, estrategia="entrada_primera_salida_ultima"):
    """Comprime ráfagas de marcaciones del mismo tipo."""
    resultado = []
    for tipo in ("Entrada", "Salida"):
        lista = [m for m in grupo if m["tipo"] == tipo]
        if not lista:
            continue
        resultado.extend(_dedupe_por_tipo(lista, segundos, mantener_ultima=(tipo == "Salida")))
    resultado.sort(key=lambda m: (m["hora"], m["tipo"]))
    return resultado


def indexar_marcaciones(marcaciones, incluir_denegados, dedupe_segundos=60,
                        dedupe_estrategia="entrada_primera_salida_ultima"):
    """Construye {clave_empleado -> {fecha -> [marc ]}} aplicando la política de denegados."""
    indice = defaultdict(lambda: defaultdict(list))
    for m in marcaciones:
        if m["situacion"] == "Permitido":
            aceptado = True
        elif m["situacion"] == "Denegado" and incluir_denegados:
            aceptado = True
        else:
            aceptado = False
        if not aceptado:
            continue
        clave = normalizar_nombre_cached(m["empleado"])
        indice[clave][m["fecha"]].append(
            {"hora": m["hora"], "tipo": m["tipo_acceso"], "situacion": m["situacion"],
             "nombre": m["empleado"], "dni": m.get("dni")}
        )
    for clave in indice:
        for fecha in indice[clave]:
            indice[clave][fecha] = _dedupe_grupo(
                indice[clave][fecha], segundos=dedupe_segundos, estrategia=dedupe_estrategia)
    return indice


class ResultadoConciliacion:
    """Contrato de salida del motor de conciliación por registro."""

    def __init__(self, registro):
        self.fila_excel = registro.get("fila_excel")
        self.fecha = registro.get("fecha")
        self.turno = registro.get("turno")
        self.empleado = registro.get("empleado")
        self.hora_inicio_orig = registro.get("hora_inicio_orig")
        self.hora_fin_orig = registro.get("hora_fin_orig")
        self.monto_total = registro.get("monto_total") or 0.0
        self.horas_declaradas = registro.get("horas_declaradas")
        self.metodo_nombre = None
        self.score = 0.0
        self.empleado_relatorio = None
        self.hora_entrada = None
        self.fecha_entrada = None
        self.hora_salida = None
        self.fecha_salida = None
        self.horas_validadas = 0.0
        self.usadas_denegadas = False
        self.marcas_encontradas = 0
        self.marcaciones_brutas = 0
        self.uso_fallback_ventana = False
        self.posible_mas12 = False
        self.puntaje_jornada = None
        self.candidatas_jornada = []
        self.motivo_jornada = None
        self.observacion = []
        self.estado = None
        self.confianza = None
        self.empresa = None
        self.cruza_medianoche = False
        self.horas_trabajadas = 0.0
        self.horas_netas = 0.0
        self.validacion_rainbow = None
        self.tipo_hhee = None
        self.dni = None
        self.jornada_nominal = None
        self.horas_extras = None
        self.he_brutas = None
        self.he_exceso_tope = 0.0
        self.duracion_txt = None
        self.sin_almuerzo_txt = None
        self.hexagesimal = None
        self.hh_rev = None
        self.tipo_rev = None
        # Split porcentual y costos (nuevo)
        self.horas_25 = 0.0
        self.horas_35 = 0.0
        self.horas_100 = 0.0
        self.costo_25 = 0.0
        self.costo_35 = 0.0
        self.costo_100 = 0.0
        self.valor_25 = 0.0
        self.valor_35 = 0.0
        self.valor_100 = 0.0
        self.valor_hhee = 0.0
        self.transporte_cant = 0
        self.transporte_valor = 0.0
        self.alimentacion_tipo = None
        self.alimentacion_valor = 0.0
        self.costo_total = 0.0
        self.especialidad = None


def conciliar(registro, marcaciones, indice_marcas, identidades, cfg):
    """Concilia un registro del consolidado contra las marcaciones.

    Devuelve un ResultadoConciliacion listo para la validación.
    """
    res = ResultadoConciliacion(registro)
    res.empresa = cfg["empresa_info"]["nombre"]
    res.descuento_comida_horas = cfg["empresa_info"].get("descuento_comida_horas", 1.0)
    turno = str(registro.get("turno") or "").strip()
    notas = []

    match = match_empleado(registro["empleado"], identidades, cfg)
    res.metodo_nombre = "NO_ENCONTRADO" if match["metodo"] == "NO_ENCONTRADO" \
        else ("AMBIGUA" if match["ambiguo"] else match["metodo"])
    res.score = match["score"]

    if match["metodo"] == "NO_ENCONTRADO":
        res.estado = "PENDIENTE"
        res.confianza = "BAJA"
        res.observacion = ["Trabajador no encontrado en el relatorio."]
        _aplicar_formato_revfinal(res, registro, cfg)
        return res

    if match["ambiguo"]:
        resolucion = _resolver_ambiguo(match, indice_marcas, registro["fecha"])
        if resolucion is None:
            res.estado = "AMBIGUO"
            res.confianza = "BAJA"
            res.observacion = ["Múltiples candidatos con score similar: %s"
                               % [(s, c) for s, c, _i in match["candidatos"]]]
            _aplicar_formato_revfinal(res, registro, cfg)
            return res
        identidad = resolucion
    else:
        identidad = match["identidad"]

    clave = identidad.clave
    res.empleado_relatorio = identidad.nombre_principal()

    dnis = sorted(d for d in (getattr(identidad, "dnis", None) or []) if d)
    if len(dnis) == 1:
        res.dni = dnis[0]
    elif len(dnis) > 1:
        res.dni = "/".join(dnis)
        notas.append("DNI multiple en RAINBOW (%s): revisar." % res.dni)

    if turno not in cfg["turnos"]:
        if len(cfg["turnos"]) > 1:
            inferido = _inferir_turno(clave, registro["fecha"], indice_marcas, cfg)
            if inferido:
                notas.append("Turno declarado '%s' no valido; se infirio %s."
                             % (turno or "vacio", inferido))
                turno = inferido
            else:
                res.estado = "ERROR"
                res.confianza = "BAJA"
                res.observacion = ["Turno '%s' no valido y no se pudo inferir uno "
                                   "de la configuracion (%s)."
                                   % (turno, ", ".join(sorted(cfg["turnos"])))]
                _aplicar_formato_revfinal(res, registro, cfg)
                return res
        else:
            res.estado = "ERROR"
            res.confianza = "BAJA"
            res.observacion = ["Turno desconocido: %s" % turno]
            _aplicar_formato_revfinal(res, registro, cfg)
            return res

    tcfg = cfg["turnos"][turno]
    res.turno = turno
    res.cruza_medianoche = bool(tcfg.get("cruza_medianoche"))
    tnominal = cfg["empresa_info"].get("turnos_configurados", {}).get(turno)
    if tnominal and "inicio" in tnominal and "fin" in tnominal:
        res.jornada_nominal = jornada_nominal_horas(tnominal)

    d, d1 = registro["fecha"], registro["fecha"] + datetime.timedelta(days=1)

    estrategia = (cfg.get("conciliacion") or {}).get("estrategia", "ventana_turno")
    if estrategia == "dia_completo":
        entradas, salidas, uso_entrada, uso_salida = _candidatas_dia_completo(
            clave, d, d1, indice_marcas, cfg)
        puntaje, candidatas = None, None
    else:
        entradas, salidas = _candidatas_marcas(turno, clave, d, d1, indice_marcas, tcfg)
        uso_entrada, uso_salida, puntaje, candidatas = _elegir_jornada(
            turno, entradas, salidas, d, d1, tcfg, indice_marcas, clave)
    res.puntaje_jornada = puntaje
    res.candidatas_jornada = candidatas

    # Ventana ampliada (regla del revisor humano RevFinal): en turnos
    # diurnos, si la ventana nominal no encontro pareja completa, se usa la
    # primera Entrada y la ultima Salida REALES del dia. Nunca se inventan:
    # son marcaciones existentes, solo se relaja la tolerancia.
    if not tcfg.get("cruza_medianoche") and (uso_entrada is None or uso_salida is None):
        fb_ent, fb_sal, motivo = _fallback_dia_completo(clave, d, indice_marcas)
        if fb_ent is not None and fb_sal is not None:
            nueva_ent = uso_entrada or fb_ent
            nueva_sal = uso_salida or fb_sal
            if (nueva_sal["fecha"], nueva_sal["hora"]) > (nueva_ent["fecha"], nueva_ent["hora"]):
                if uso_entrada is None:
                    uso_entrada = fb_ent
                if uso_salida is None:
                    uso_salida = fb_sal
                res.uso_fallback_ventana = True
                notas.append(motivo)

    if (res.cruza_medianoche and uso_entrada and puntaje is not None
            and puntaje < tcfg.get("puntaje_minimo", 55)):
        res.estado = "REVISIÓN MANUAL"
        res.confianza = "BAJA"

    usadas_denegadas = bool(
    (uso_entrada and uso_entrada["situacion"] == "Denegado") or
    (uso_salida and uso_salida["situacion"] == "Denegado"))
    res.usadas_denegadas = usadas_denegadas
    res.marcas_encontradas = len(entradas) + len(salidas)
    res.marcaciones_brutas = len(indice_marcas.get(clave, {}).get(d, [])) \
        + len(indice_marcas.get(clave, {}).get(d1, []))

    if uso_entrada and uso_salida:
        dt_ent = datetime.datetime.combine(uso_entrada["fecha"], uso_entrada["hora"])
        dt_sal = datetime.datetime.combine(uso_salida["fecha"], uso_salida["hora"])
        res.horas_trabajadas = horas_trabajadas(dt_ent, dt_sal)
        res.horas_netas = horas_netas(res.horas_trabajadas,
                                      res.descuento_comida_horas)
        if tnominal and res.jornada_nominal is not None:
            he = calcular_horas_extras(res.horas_trabajadas, tnominal,
                                       cfg["empresa_info"])
            res.horas_extras = he["pagables"]
            res.he_brutas = he["brutas"]
            res.he_exceso_tope = he["exceso_sobre_tope"]
            if he["exceso_sobre_tope"] > 0:
                notas.append(
                    "HE reales %.2f h superan el maximo de sobretiempo %s h; "
                    "se pagan %.2f h."
                    % (he["brutas"], cfg["empresa_info"].get("sobretiempo_maximo"),
                       he["pagables"]))

    _construir_observacion(res, uso_entrada, uso_salida, cfg, indice_marcas, clave, notas)

    jornada_completa = bool(res.hora_entrada and res.hora_salida)
    vc = cfg.get("salida", {}).get("validacion_rainbow", {})
    res.validacion_rainbow = vc.get("si", "SI") if jornada_completa else vc.get("no", "NO")
    res.tipo_hhee = clasificar_tipo_hhee(
        res.horas_trabajadas if jornada_completa else None, cfg)
    _aplicar_formato_revfinal(res, registro, cfg)

    # --- Costos de HHEE: split 25%/35%/100%, tarifas, transporte, alimentación ---
    res.especialidad = registro.get("especialidad") or ""
    tipo_upper = str(res.tipo_rev or "").strip().upper()
    he_effective = res.hh_rev if res.hh_rev is not None else (res.horas_extras or 0.0)
    sp = split_porcentajes(he_effective, tipo_upper, res.hexagesimal)
    res.horas_25 = sp["h25"]
    res.horas_35 = sp["h35"]
    res.horas_100 = sp["h100"]

    tabla_costos = cfg.get("_tabla_costos")
    tarifa = tabla_costos.lookup(res.especialidad) if tabla_costos else None
    if tarifa:
        res.costo_25 = tarifa.costo_25
        res.costo_35 = tarifa.costo_35
        res.costo_100 = tarifa.costo_100
    if tarifa:
        from costos import calcular_valor_hhee
        vh = calcular_valor_hhee(res.horas_25, res.horas_35, res.horas_100, tarifa)
        res.valor_25 = vh["valor_25"]
        res.valor_35 = vh["valor_35"]
        res.valor_100 = vh["valor_100"]
        res.valor_hhee = vh["valor_total"]

    if jornada_completa:
        from costos import calcular_transporte, calcular_alimentacion
        # Cantidad de personas: prioriza el dato real del Excel (Cantidad
        # Movilidad), si existe; si no, el npersonas declarado; en ultimo
        # caso 1 trabajador.
        ve = registro.get("valores_excel") or {}
        cant_excel = _to_int(ve.get("transporte_cant"))
        np = cant_excel if cant_excel else _to_int(registro.get("npersonas"))
        if not np:
            np = 1
        tr = calcular_transporte(np, cfg)
        res.transporte_cant = tr["cantidad"]
        res.transporte_valor = tr["valor"]
        al = calcular_alimentacion(res.turno, cfg, res.hh_rev)
        if jornada_completa and res.horas_trabajadas > 0:
            res.alimentacion_tipo = al["tipo"]
            res.alimentacion_valor = al["valor"]
        res.costo_total = round(
            res.valor_hhee
            + (res.transporte_cant * res.transporte_valor)
            + res.alimentacion_valor, 2)
    else:
        res.alimentacion_tipo = "SIN ALIMENTACION"

    return res


def _fallback_dia_completo(clave, d, indice_marcas):
    """Primera Entrada y ultima Salida del dia, sin restriccion de ventana.

    Replica la regla del revisor humano del RevFinal: si las ventanas
    nominales (tolerancias de config) no capturaron la pareja, pero el
    trabajador SI tiene marcas Entrada/Salida ese dia, se usan las reales.
    Devuelve (entrada|None, salida|None, motivo).
    """
    marcas = indice_marcas.get(clave, {}).get(d, [])
    entradas = [m for m in marcas if m["tipo"] == "Entrada"]
    salidas = [m for m in marcas if m["tipo"] == "Salida"]
    if not entradas or not salidas:
        return None, None, None
    ent = min(entradas, key=lambda m: m["hora"])
    sal = max(salidas, key=lambda m: m["hora"])
    if sal["hora"] <= ent["hora"]:
        return None, None, None
    motivo = ("VENTANA AMPLIADA: se usa la primera Entrada (%s) y la ultima "
              "Salida (%s) del dia; alguna cae fuera de la ventana nominal."
              % (ent["hora"], sal["hora"]))
    return dict(ent, fecha=d), dict(sal, fecha=d), motivo


def _fmt_hms(segundos):
    segundos = int(round(segundos))
    h, rem = divmod(segundos, 3600)
    m, s = divmod(rem, 60)
    return "%02d:%02d:%02d" % (h, m, s)


def _aplicar_formato_revfinal(res, registro, cfg):
    """Calcula las columnas del formato RevFinal (H-H REV, TIPO, duraciones).

    Reglas replicadas de la revision manual (CONSOLIDADO - ENERO RevFinal):
    - TIPO se clasifica por las horas DECLARADAS (H-H del correo): >=7 h y
      <=12 h -> ACTIVACION; >12 h -> REVISAR EN RAINBOW; resto SOBRETIEMPO.
    - SOBRETIEMPO: BD (hexagesimal) es la jornada BRUTA (BA-AZ) y
      H-H REV = max(0, BD - nominal 9.6 h).
    - ACTIVACION: se paga la jornada NETA (menos 1 h de almuerzo): tanto BD
      como H-H REV son el hexagesimal de BB - almuerzo.
    - BB = BA-AZ en HH:MM:SS; BC = BB - almuerzo (solo si BB > 1 h).
    """
    cls = cfg.get("clasificacion_hhee") or {}
    nominal = float(cls.get("turno_nominal_horas", 9.6))
    act_min = float(cls.get("activacion_min_horas", 7.0))
    act_max = float(cls.get("activacion_max_horas", 12.0))
    col_act = cls.get("activacion_col", "ACTIVACION")
    col_sob = cls.get("sobretiempo_col", "SOBRETIEMPO")
    col_rev = cls.get("revisar_col", "REVISAR EN RAINBOW")
    descuento_seg = float(cfg.get("jornada", {}).get("descuento_comida_horas",
                                                     1.0)) * 3600.0

    declaradas = registro.get("horas_declaradas")
    try:
        declaradas_f = float(declaradas) if declaradas not in (None, "") else None
    except (TypeError, ValueError):
        declaradas_f = None

    base = declaradas_f if declaradas_f is not None else (res.horas_trabajadas or 0.0)
    if base > act_max:
        res.tipo_rev = col_rev
    elif base >= act_min:
        res.tipo_rev = col_act
    else:
        res.tipo_rev = col_sob

    if not (res.hora_entrada and res.hora_salida):
        res.hh_rev = 0.0
        return

    dt_ent = datetime.datetime.combine(res.fecha_entrada, res.hora_entrada)
    dt_sal = datetime.datetime.combine(res.fecha_salida, res.hora_salida)
    seg = max(0.0, (dt_sal - dt_ent).total_seconds())
    res.duracion_txt = _fmt_hms(seg)
    if seg > descuento_seg:
        res.sin_almuerzo_txt = _fmt_hms(seg - descuento_seg)

    if res.tipo_rev == col_rev:
        res.hexagesimal = round(seg / 3600.0, 2)
        res.hh_rev = None
    elif res.tipo_rev == col_act:
        base_seg = seg - descuento_seg if seg > descuento_seg else seg
        res.hexagesimal = round(base_seg / 3600.0, 2)
        res.hh_rev = res.hexagesimal
    else:
        res.hexagesimal = round(seg / 3600.0, 2)
        res.hh_rev = round(max(0.0, res.hexagesimal - nominal), 2)


def _candidatas_dia_completo(clave, d, d1, indice_marcas, cfg):
    """Estrategia 'dia_completo': jornada = primera Entrada a última Salida.

    El bloque diario abarca el día declarado completo más la madrugada del
    día siguiente hasta fin_madrugada (config, por defecto 08:00). Replica
    el criterio de la revisión manual: se usa la jornada completa del día
    (ej. 07:19->17:55) en lugar del fragmento de madrugada.
    """
    fin_mad_min = hora_a_minutos(
        (cfg.get("conciliacion") or {}).get("fin_madrugada", "08:00"))
    marcas_persona = indice_marcas.get(clave, {})

    def en_bloque(marca, fecha):
        if fecha == d:
            return True
        return _a_minutos(marca["hora"]) <= fin_mad_min

    entradas = sorted(
        (dict(m, fecha=f) for f in (d, d1) for m in marcas_persona.get(f, [])
         if m["tipo"] == "Entrada" and en_bloque(m, f)),
        key=lambda m: (m["fecha"], m["hora"]))
    salidas = sorted(
        (dict(m, fecha=f) for f in (d, d1) for m in marcas_persona.get(f, [])
         if m["tipo"] == "Salida" and en_bloque(m, f)),
        key=lambda m: (m["fecha"], m["hora"]))

    entrada = entradas[0] if entradas else None
    if entrada is not None:
        posteriores = [s for s in salidas
                       if (s["fecha"], s["hora"]) > (entrada["fecha"], entrada["hora"])]
        salida = posteriores[-1] if posteriores else None
    else:
        salida = salidas[-1] if salidas else None
    return entradas, salidas, entrada, salida


def _inferir_turno(clave, fecha, indice_marcas, cfg):
    """Infiere el turno más probable desde la configuración de la empresa.

    Cuenta las marcas de Entrada/Salida que caen en las ventanas de cada
    turno configurado para el día declarado y el siguiente; gana el turno
    con más coincidencias. Si hay empate, devuelve None (nunca elige al azar).
    """
    d = fecha
    d1 = fecha + datetime.timedelta(days=1)
    puntajes = {}
    for t, tcfg in cfg["turnos"].items():
        entradas, salidas = _candidatas_marcas(t, clave, d, d1, indice_marcas, tcfg)
        puntajes[t] = len(entradas) + len(salidas)
    mejor = max(puntajes, key=puntajes.get)
    if puntajes[mejor] == 0:
        return None
    empates = sorted(t for t, n in puntajes.items() if n == puntajes[mejor])
    if len(empates) > 1:
        return None
    return mejor


def _candidatas_marcas(turno, clave, d, d1, indice_marcas, tcfg):
    """Devuelve marcaciones Entrada/Salida dentro de las ventanas del turno.

    Sin cruce de medianoche (T1 y T3 diurnos): solo el día declarado.
    Con cruce (turnos que terminan al día siguiente): el día declarado
    (entrada vespertina/salida tardía) y el día siguiente (madrugada/salida).
    """
    def marcas(fecha):
        return indice_marcas.get(clave, {}).get(fecha, [])

    if tcfg.get("cruza_medianoche"):
        rango_ent = {d: _rango(tcfg["entrada_dia_d"]), d1: _rango(tcfg["entrada_dia_dmas1"])}
        rango_sal = {d1: _rango(tcfg["salida_dia_dmas1"])}
        rango_sal_d = tcfg.get("salida_mismo_dia")
        if rango_sal_d:
            rango_sal[d] = _rango(rango_sal_d)
    else:
        rango_ent = {d: _rango(tcfg["entrada"])}
        rango_sal = {d: _rango(tcfg["salida"])}

    entradas = [dict(m, fecha=f) for f, rango in rango_ent.items()
                for m in marcas(f) if m["tipo"] == "Entrada"
                and _en_ventana(m["hora"], rango)]
    salidas = [dict(m, fecha=f) for f, rango in rango_sal.items()
               for m in marcas(f) if m["tipo"] == "Salida"
               and _en_ventana(m["hora"], rango)]
    entradas.sort(key=lambda m: (m["fecha"], m["hora"]))
    salidas.sort(key=lambda m: (m["fecha"], m["hora"]))
    return entradas, salidas


def _elegir_jornada(turno, entradas, salidas, d, d1, tcfg, indice_marcas=None, clave=None):
    """Elige la pareja entrada/salida representativa de la jornada.

    Sin cruce de medianoche: primera Entrada y última Salida del día
    declarado (ráfagas ya comprimidas). Con cruce: la entrada es la primera
    marca Entrada de la ventana (D vespertina o madrugada D+1) y la salida
    se elige por puntaje, para no asociar a una jornada una salida de otra
    mini-jornada (por ejemplo una Entrada intermedia rompe la secuencia).
    """
    if not tcfg.get("cruza_medianoche"):
        entrada = entradas[0] if entradas else None
        salida = salidas[-1] if salidas else None
        return entrada, salida, None, None

    ventana_horas = tcfg.get("ventana_busqueda_horas", 19)
    entrada = entradas[0] if entradas else None
    if entrada is None:
        return None, (salidas[0] if salidas else None), None, None

    candidatas = [s for s in salidas if _dentro_ventana(entrada, s, ventana_horas)]
    puntuadas = [(_calculate_score_salida(entrada, s, d, tcfg, indice_marcas, clave), s)
                 for s in candidatas]
    mejor_punt, mejor_salida = None, None
    for punt, s in puntuadas:
        if mejor_salida is None:
            mejor_punt, mejor_salida = punt, s
        elif punt[0] > mejor_punt[0] or (
                punt[0] == mejor_punt[0]
                and (s["fecha"], s["hora"]) > (mejor_salida["fecha"], mejor_salida["hora"])):
            mejor_punt, mejor_salida = punt, s
    return entrada, mejor_salida, (mejor_punt[0] if mejor_punt else None), \
        [{"fecha": s["fecha"], "hora": s["hora"], "situacion": s["situacion"],
          "puntaje": p[0], "duracion_h": p[1]} for p, s in puntuadas]


def _calculate_score_salida(entrada, salida, d, tcfg, indice_marcas, clave):
    """Puntaje de coherencia de la pareja entrada->salida en T2 (0-90).

    Suma +40 si la duración cae en el rango típico (distinto si la entrada
    es de madrugada D+1), +20 si la salida cae en la madrugada típica y
    +30/-30 según haya o no una Entrada intermedia (una Entrada en medio
    indica que la salida pertenece a otra mini-jornada).
    """
    dt_ent = datetime.datetime.combine(entrada["fecha"], entrada["hora"])
    dt_sal = datetime.datetime.combine(salida["fecha"], salida["hora"])
    dur = (dt_sal - dt_ent).total_seconds() / 3600.0

    rango = tcfg.get("rango_duracion_horas", [6, 16])
    if entrada["fecha"] > d:
        rango = tcfg.get("rango_duracion_madrugada_horas", [0.5, 8])

    puntaje = 0
    if rango[0] <= dur <= rango[1]:
        puntaje += 40
    rango_dawn = _rango(tcfg.get("madrugada_horas"))
    if rango_dawn and _en_ventana(salida["hora"], rango_dawn):
        puntaje += 20
    if _entradas_intermedias(indice_marcas, clave, dt_ent, dt_sal,
                             tcfg.get("pausa_nueva_jornada_min", 60)) == 0:
        puntaje += 30
    else:
        puntaje -= 30
    return puntaje, round(dur, 2)


def _entradas_intermedias(indice_marcas, clave, dt_ent, dt_sal, pausa_min=60):
    """Cuenta Entradas que inician una NUEVA jornada entre entrada y salida.

    Una Entrada solo rompe la secuencia si llega tras una Salida con una
    pausa >= pausa_min: una excursión corta dentro de la misma jornada
    (18:45 Salida -> 18:55 Entrada) no rompe nada; una Entrada tras 7:30 h
    de ausencia (23:47 -> 07:15) sí inicia otra jornada.

    Rendimiento v1.1: solo se recorren los días dentro del rango de la
    pareja (antes se barria el historial completo del empleado).
    """
    if indice_marcas is None or clave is None:
        return 0
    eventos = []
    dia_min, dia_max = dt_ent.date(), dt_sal.date()
    marcas_persona = indice_marcas.get(clave, {})
    for fecha in sorted(f for f in marcas_persona if dia_min <= f <= dia_max):
        for m in marcas_persona[fecha]:
            dt = datetime.datetime.combine(fecha, m["hora"])
            if dt_ent < dt < dt_sal:
                eventos.append((dt, m["tipo"]))
    eventos.sort(key=lambda x: x[0])
    ultima_salida = None
    rupturas = 0
    for dt, tipo in eventos:
        if tipo == "Salida":
            ultima_salida = dt
        elif ultima_salida is not None and \
                (dt - ultima_salida).total_seconds() / 60.0 >= pausa_min:
            rupturas += 1
            ultima_salida = None
    return rupturas


def _dentro_ventana(entrada, salida, horas):
    dt_ent = datetime.datetime.combine(entrada["fecha"], entrada["hora"])
    dt_sal = datetime.datetime.combine(salida["fecha"], salida["hora"])
    delta = (dt_sal - dt_ent).total_seconds() / 3600.0
    return 0 < delta <= horas


def _aviso_cambio_turno(res, indice_marcas, clave, obs):
    """Detecta jornada vespertina (tipo T3) aunque el turno declarado sea T1.

    Solo informa en el log (decisión del negocio: no se auto-escribe
    CAMBIO/ADELANTO DE TURNO en el Excel, se revisan caso a caso).
    """
    marcas_dia = indice_marcas.get(clave, {}).get(res.fecha, [])
    entradas = [m for m in marcas_dia
                if m["tipo"] == "Entrada" and m["hora"].hour >= 12]
    salidas = [m for m in marcas_dia
               if m["tipo"] == "Salida" and m["hora"].hour >= 18]
    if entradas and salidas:
        obs.append("Posible CAMBIO DE TURNO a T3 (jornada vespertina en el día declarado).")


def _construir_observacion(res, uso_entrada, uso_salida, cfg, indice_marcas, clave, notas=None):
    tcfg = cfg["turnos"].get(res.turno, {})
    obs = list(notas or [])
    if res.empresa and res.empresa != "GENERICA":
        cfg_t = cfg["empresa_info"].get("turnos_configurados", {}).get(res.turno)
        if cfg_t:
            obs.append("Config %s %s: %s-%s%s"
                       % (res.empresa, res.turno, cfg_t.get("inicio"), cfg_t.get("fin"),
                          " (cruza medianoche)" if res.cruza_medianoche else ""))
    obs.append("Nombre: %s (score %.2f)" % (res.metodo_nombre or "NO_ENCONTRADO", res.score))
    obs.append("%d marcaciones encontradas en ventana" % res.marcas_encontradas)
    if res.metodo_nombre == "EXACTA":
        obs.append("Coincidencia normalizada exacta.")
    elif res.metodo_nombre == "DIFUSA":
        obs.append("Coincidencia difusa. Score=%.2f." % res.score)

    if uso_entrada:
        res.hora_entrada = uso_entrada["hora"]
        res.fecha_entrada = uso_entrada["fecha"]
        if res.cruza_medianoche and uso_entrada["fecha"] > res.fecha:
            obs.append("Entrada encontrada en la madrugada del día siguiente.")
        else:
            obs.append("Entrada: %s %s" % (uso_entrada["fecha"], uso_entrada["hora"]))
        if not res.cruza_medianoche:
            if uso_entrada["hora"].hour < 5:
                obs.append("Posible ADELANTO DE TURNO (entrada antes de 05:00).")
            elif uso_entrada["hora"].hour >= 12:
                obs.append("Posible CAMBIO DE TURNO a T3 (marcaciones vespertinas).")
    else:
        obs.append("No se encontró entrada válida.")

    if uso_salida:
        res.hora_salida = uso_salida["hora"]
        res.fecha_salida = uso_salida["fecha"]
        if res.cruza_medianoche and uso_salida["fecha"] > res.fecha:
            obs.append("Salida encontrada al día siguiente.")
        else:
            obs.append("Salida: %s %s" % (uso_salida["fecha"], uso_salida["hora"]))
    else:
        obs.append("No se encontró salida válida.")

    if res.cruza_medianoche and uso_entrada and uso_salida:
        obs.append("Motivo pareja nocturna: entrada = 1ª marca Entrada en ventana "
                   "(D vespertina o madrugada D+1)")
        if res.puntaje_jornada is not None:
            obs.append("salida elegida por puntaje %d" % res.puntaje_jornada)
        for c in (res.candidatas_jornada or [])[1:]:
            obs.append("candidata descartada: %s %s (punt %d, %.1fh)"
                       % (c["fecha"], c["hora"], c["puntaje"], c["duracion_h"]))

    if res.estado == "REVISIÓN MANUAL":
        obs.append("Pareja poco concluyente: requiere REVISIÓN MANUAL.")

    if res.usadas_denegadas:
        obs.append("Se usaron marcaciones denegadas (evidencia de presencia).")

    if not uso_entrada and not res.cruza_medianoche:
        _aviso_cambio_turno(res, indice_marcas, clave, obs)

    if res.hora_entrada and res.hora_salida:
        dt_ent = datetime.datetime.combine(res.fecha_entrada, res.hora_entrada)
        dt_sal = datetime.datetime.combine(res.fecha_salida, res.hora_salida)
        res.horas_validadas = round(max(0.0, (dt_sal - dt_ent).total_seconds() / 3600.0), 4)
        if res.horas_trabajadas > 0:
            obs.append("Horas trabajadas: %.4f h | Horas netas (menos %.1f h de comida): %.4f h"
                       % (res.horas_trabajadas, res.descuento_comida_horas, res.horas_netas))
        comentarios = cfg.get("comentarios", {})
        if comentarios.get("mas12_activo", False) and \
                res.horas_validadas >= comentarios.get("mas12_umbral_horas", 12.0):
            hh = int(res.horas_validadas)
            mm = int(round((res.horas_validadas - hh) * 60))
            obs.append("Posible +12 horas (duración real %d:%02d)." % (hh, mm))
            res.posible_mas12 = True

    res.observacion = " | ".join(obs)


def _resolver_ambiguo(match, indice_marcas, fecha):
    """Si hay empate de candidatos, resuelve por quién tiene marcaciones.

    Devuelve la Identidad del único candidato con marcaciones en la fecha
    objetivo (o None si hay 0 o más de uno).
    """
    fechas = {fecha, fecha + datetime.timedelta(days=1)}
    con_marcas = []
    for _score, _clave, identidad in match["candidatos"]:
        total = 0
        for f in fechas:
            total += sum(1 for _ in indice_marcas.get(identidad.clave, {}).get(f, []))
        if total > 0:
            con_marcas.append(identidad)
    return con_marcas[0] if len(con_marcas) == 1 else None