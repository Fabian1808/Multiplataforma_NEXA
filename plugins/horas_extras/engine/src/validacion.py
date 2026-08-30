"""Validación: asigna estado y nivel de confianza a cada resultado.

Estados: VALIDADO, OBSERVADO, PENDIENTE, AMBIGUO, SIN MARCACIÓN,
SIN ENTRADA, SIN SALIDA, REVISIÓN MANUAL, ERROR.

Confianza: ALTA, MEDIA, BAJA. Combinación del método/score de nombre
con la calidad de la evidencia de marcación.
"""


def validar_respuesta(res, cfg):
    """Rellena res.estado y res.confianza a partir de la evidencia obtenida."""
    _asignar_estado(res)
    _asignar_confianza(res, cfg)
    return res


def _asignar_estado(res):
    if res.estado in ("ERROR", "PENDIENTE", "AMBIGUO", "REVISIÓN MANUAL"):
        return
    tiene_entrada = res.hora_entrada is not None
    tiene_salida = res.hora_salida is not None

    if res.marcas_encontradas == 0 and res.marcaciones_brutas == 0:
        res.estado = "SIN MARCACIÓN"
    elif not tiene_entrada and not tiene_salida:
        res.estado = "OBSERVADO"
    elif tiene_entrada and tiene_salida:
        res.estado = "VALIDADO"
    elif tiene_entrada:
        res.estado = "SIN SALIDA"
    else:
        res.estado = "SIN ENTRADA"


def _asignar_confianza(res, cfg):
    if res.estado in ("ERROR", "PENDIENTE", "AMBIGUO", "REVISIÓN MANUAL",
                      "SIN MARCACIÓN", "SIN ENTRADA"):
        res.confianza = "BAJA"
        return
    if res.estado in ("SIN SALIDA", "OBSERVADO"):
        res.confianza = "MEDIA"
        return

    res.confianza = "ALTA"
    if res.usadas_denegadas:
        res.confianza = cfg.get("confianza", {}).get("denegados_rebaja_a", "MEDIA")
        return
    elif res.metodo_nombre == "DIFUSA" and res.score < cfg["confianza"]["difusa_score_min_alta"]:
        res.confianza = "MEDIA"
        return
    # La pareja se obtuvo ampliando la tolerancia nominal (marcas reales
    # fuera de ventana): evidencia valida pero atipica -> maximo MEDIA.
    if getattr(res, "uso_fallback_ventana", False):
        res.confianza = "MEDIA"