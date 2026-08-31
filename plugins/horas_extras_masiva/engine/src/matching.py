"""Similitud difusa de texto/biblioteca sin dependencias externas.

Implementa normalización token-set y ratio token-set al estilo RapidFuzz
usando solo la biblioteca estándar (difflib). Suficiente para matching de
nombres de empleados y cargos.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from utiles import normalizar_texto


def ratio_exacto(a: str, b: str) -> float:
    """Ratio clásico 0..100 entre dos cadenas."""
    na = normalizar_texto(a)
    nb = normalizar_texto(b)
    if not na and not nb:
        return 100.0
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio() * 100.0


def _tokens_sorted(s: str):
    return sorted(normalizar_texto(s).split())


def ratio_token_set(a: str, b: str) -> float:
    """Ratio token-set: compara el conjunto de tokens, robusto a orden/repetición."""
    ta = _tokens_sorted(a)
    tb = _tokens_sorted(b)
    if not ta or not tb:
        return ratio_exacto(a, b)
    mayor, menor = (ta, tb) if len(ta) >= len(tb) else (tb, ta)
    menor_set = set(menor)
    interseccion = [t for t in mayor]
    inter_set = set(interseccion) & menor_set
    if not inter_set:
        base = 0.0
    else:
        base = SequenceMatcher(None, " ".join(inter_set), " ".join(menor)).ratio() * 100.0
    # penalización por tokens que sobran (token parciales)
    sobra = len(set(interseccion) - menor_set) + len(menor_set - set(interseccion))
    penal = max(0.0, (len(menor) - len(inter_set)) * 8.0)
    puntaje = base - penal
    # si un nombre es subconjunto del otro, da alta confianza
    if inter_set == menor_set and len(mayor) >= len(menor):
        puntaje = max(puntaje, 95.0)
    return max(0.0, min(100.0, puntaje))


def ratio_token_sort(a: str, b: str) -> float:
    ta = " ".join(_tokens_sorted(a))
    tb = " ".join(_tokens_sorted(b))
    return SequenceMatcher(None, ta, tb).ratio() * 100.0


def mejor_token(a: str, b: str) -> float:
    """Usa el mejor de token-set / token-sort."""
    return max(ratio_token_set(a, b), ratio_token_sort(a, b))


def filtrar_candidatos(consulta, candidatos, umbral: float = 60.0, max_candidatos: int = 5):
    """Devuelve lista de (candidato, puntaje) ordenada por puntaje descendente."""
    resultados = []
    for c in candidatos:
        if not c:
            continue
        r = mejor_token(consulta, c)
        if r >= umbral:
            resultados.append((c, r))
    resultados.sort(key=lambda x: x[1], reverse=True)
    return resultados[:max_candidatos]
