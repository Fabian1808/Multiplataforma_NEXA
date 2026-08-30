"""Version unica de la aplicacion (semver X.Y.Z).

Unica fuente de verdad para la version del producto. La GUI, el --smoke,
el log de la aplicacion y el actualizador leen de aqui.

Convencion semver:
  X.Y.Z
  X = cambio mayor (rompe comportamiento/formatos)
  Y = nuevas funcionalidades
  Z = correcciones
"""

VERSION = "1.0.0"

NOMBRE_APP = "Aplicativo Rainbow"
NOMBRE_CORTO = "Aplicativo Rainbow"
AUTOR = "NEXA"
COPYRIGHT = "Copyright (c) 2026 NEXA"


def comparar(a, b):
    """Compara dos versiones semver 'X.Y.Z' (admite 'X.Y' o 'X').

    Devuelve -1 si a < b, 0 si iguales, 1 si a > b. Lanza ValueError si
    alguna no es semver valida.
    """
    def _trozos(v):
        partes = str(v).strip().split(".")
        if len(partes) > 3:
            raise ValueError("Version invalida: %r" % (v,))
        numeros = []
        for p in partes:
            if not p.isdigit():
                raise ValueError("Version invalida: %r" % (v,))
            numeros.append(int(p))
        while len(numeros) < 3:
            numeros.append(0)
        return numeros
    a_num = _trozos(a)
    b_num = _trozos(b)
    if a_num < b_num:
        return -1
    if a_num > b_num:
        return 1
    return 0


def actual():
    """Devuelve la version actual de la aplicacion."""
    return VERSION