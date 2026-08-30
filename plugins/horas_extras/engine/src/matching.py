"""Matching de empleados entre consolidado y relatorio.

Estrategia en niveles:
  1. Coincidencia exacta normalizada
  2. Coincidencia por tokens
  3. Coincidencia difusa (RapidFuzz si está disponible, si no difflib)
  4. Cobertura tolerante (v0.2.0): fusión de tokens adyacentes
     (GIAN CARLO = GIANCARLO), subcadena y edición <=1 (MELISSA ~ MELISA),
     con pisos de autorización para no crear falsos positivos.

Nunca se elige arbitrariamente entre candidatos: si los dos primeros
están a menos de `margen_ambiguo` puntos, se resuelve por evidencia
(quién tiene marcaciones) o se devuelve AMBIGUO.
"""

from normalizacion import normalizar_nombre, normalizar_nombre_cached, tokens


class Identidad:
    """Una persona identificada en el relatorio por un nombre normalizado."""

    def __init__(self, clave):
        self.clave = clave
        self.nombres_raw = set()
        self.dnis = set()

    def nombre_principal(self):
        return sorted(self.nombres_raw, key=lambda n: -len(n))[0] if self.nombres_raw else self.clave


def construir_indice(marcaciones):
    """Construye {nombre_normalizado -> Identidad} desde las marcaciones."""
    indice = {}
    for m in marcaciones:
        clave = normalizar_nombre_cached(m["empleado"])
        if not clave:
            continue
        identidad = indice.setdefault(clave, Identidad(clave))
        identidad.nombres_raw.add(m["empleado"])
        if m.get("dni"):
            identidad.dnis.add(str(m["dni"]).strip())
    return indice


def _ratio_difuso(a, b):
    score_fuzzy = None
    try:
        from rapidfuzz import fuzz
        score_fuzzy = fuzz.token_sort_ratio(a, b)
        ca, cb = set(a.split()), set(b.split())
        if ca and cb and score_fuzzy >= 55.0:
            cobertura = len(ca & cb) / min(len(ca), len(cb)) * 100
            score_fuzzy = max(score_fuzzy, cobertura)
    except ImportError:
        score_fuzzy = None
    return min(score_fuzzy, 100.0) if score_fuzzy is not None else None


def _ratio_difflib(a, b, usar_token_sort=True):
    """Score 0-100 combinando ratio directo, tokens ordenados y cobertura.

    La cobertura de tokens (intersección / nombre más corto) solo cuenta
    cuando el ratio directo supera un piso, para evitar falsos positivos
    con nombres parciales.
    """
    from difflib import SequenceMatcher

    def ratio(x, y):
        return SequenceMatcher(None, x, y).ratio() * 100

    puntaje = ratio(a, b)
    if usar_token_sort:
        tokens_a = " ".join(sorted(a.split()))
        tokens_b = " ".join(sorted(b.split()))
        puntaje = max(puntaje, ratio(tokens_a, tokens_b))
    ca, cb = set(a.split()), set(b.split())
    if ca and cb and puntaje >= 55.0:
        cobertura = len(ca & cb) / min(len(ca), len(cb)) * 100
        puntaje = max(puntaje, cobertura)
    return min(puntaje, 100.0)


def _score_difuso(a, b):
    """Score 0-100 combinando rapidfuzz (si existe) y difflib."""
    rap = _ratio_difuso(a, b)
    if rap is not None:
        return rap
    return _ratio_difflib(a, b)


def _edicion(a, b):
    """Distancia de edición (Levenshtein) entre dos cadenas."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        fila = [i]
        for j, cb in enumerate(b, 1):
            fila.append(min(fila[-1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)))
        prev = fila
    return prev[-1]


def _cobertura_tolerante(lista_a, lista_b, cfg_alias):
    """Cobertura con alias entre los tokens de dos nombres.

    Devuelve 100.0 solo si la cobertura es COMPLETA y AUTORIZADA, si no 0.0:
    - Fusión de tokens adyacentes (GIAN CARLO -> GIANCARLO) sin piso, porque
      exige la concatenación exacta de un bloque contiguo.
    - Subcadena y edición (MELISSA ~ MELISA) solo si la cobertura estándar
      ya supera el piso (los apellidos coinciden), para no confundir
      nombres parciales (CARDENAS LUIS vs CARDENAS LUISA → NO match).
    """
    n = len(lista_a)
    if not n:
        return 0.0
    b_set = set(lista_b)
    estandar = len(set(lista_a) & b_set) / n * 100

    fusionados = set()
    i = 0
    while i < n:
        t = lista_a[i]
        if i + 1 < n and t not in b_set and (t + lista_a[i + 1]) in b_set:
            fusionados.add(t)
            fusionados.add(lista_a[i + 1])
            i += 2
            continue
        i += 1
    cobertura_fusion = len((set(lista_a) & b_set) | fusionados) / n * 100
    if cobertura_fusion >= 90.0:
        return 100.0

    piso = cfg_alias.get("piso_cobertura_alias", 60)
    if estandar < piso:
        return 0.0

    cubiertos = set(lista_a) & b_set
    len_min = cfg_alias.get("len_min_substring", 4)
    edicion_max = cfg_alias.get("edicion_max", 1)
    for t in lista_a:
        if t in cubiertos:
            continue
        for tb in lista_b:
            if len(t) >= len_min and (t in tb or _edicion(t, tb) <= edicion_max):
                cubiertos.add(t)
                break
    return 100.0 if len(cubiertos) / n * 100 >= 90.0 else 0.0


def _score_con_alias(nombre, clave, cfg):
    """Score difuso ampliado opcionalmente con la cobertura tolerante."""
    puntaje = _score_difuso(nombre, clave)
    alias = cfg["matching"].get("alias")
    if alias and alias.get("activo", False):
        extra = _cobertura_tolerante(nombre.split(), clave.split(), alias)
        if extra > puntaje:
            puntaje = extra
    return puntaje


def _mejores_candidatos(nombre, indice, cfg):
    """Devuelve lista ordenada de (score, clave_identidad) por nombre difuso."""
    candidatos = []
    for clave in indice:
        puntaje = _score_con_alias(nombre, clave, cfg)
        if puntaje >= cfg["matching"]["umbral_difusa_min"]:
            candidatos.append((puntaje, clave))
    candidatos.sort(key=lambda x: (-x[0], x[1]))
    return candidatos[: cfg["matching"]["candidatos_max"]]


def match_empleado(nombre, indice, cfg):
    """Empareja `nombre` del consolidado contra el índice del relatorio.

    Devuelve dict:
      metodo: EXACTA | DIFUSA | NO_ENCONTRADO
      identidad: Identidad o None
      score: 0-100
      candidatos: lista de (score, clave) para diagnóstico (AMBIGUO)
      ambiguo: True si hay empate de candidatos cercanos sin evidencia

    Rendimiento: si cfg trae "_match_cache" (dict compartido por el motor),
    el resultado se memoiza por nombre — el difuso es caro y los mismos
    nombres se repiten en muchas filas del consolidado.
    """
    normalizado = normalizar_nombre_cached(nombre)
    cache = cfg.get("_match_cache") if isinstance(cfg, dict) else None
    if cache is not None and normalizado in cache:
        return cache[normalizado].copy()

    if normalizado in indice:
        resultado = {"metodo": "EXACTA", "identidad": indice[normalizado],
                     "score": 100.0, "candidatos": [], "ambiguo": False}
    else:
        mejores = _mejores_candidatos(normalizado, indice, cfg)
        if not mejores:
            resultado = {"metodo": "NO_ENCONTRADO", "identidad": None,
                         "score": 0.0, "candidatos": [], "ambiguo": False}
        else:
            margen = cfg["matching"]["margen_ambiguo"]
            empate = len(mejores) >= 2 and (mejores[0][0] - mejores[1][0]) <= margen
            mejor = mejores[0][1]
            resultado = {"metodo": "DIFUSA", "identidad": indice[mejor],
                         "score": round(mejores[0][0], 2),
                         "candidatos": [(round(s, 2), c, indice[c]) for s, c in mejores],
                         "ambiguo": empate}
    if cache is not None:
        cache[normalizado] = resultado
    return resultado.copy()