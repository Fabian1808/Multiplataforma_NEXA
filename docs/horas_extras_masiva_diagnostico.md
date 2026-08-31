# HORAS EXTRAS MASIVA — diagnostico y diseno (A–J)

Diagnóstico formal que precipita la evolución del módulo **Asistencia Masiva
(Rainbow)** hacia **HORAS EXTRAS MASIVA**, usando los archivos reales del repo.

---

## A. Estructura de datos encontrada

### RAINBOW (marcaciones) — hoja `Sheet1`
`Tipo | Grupo Empresa | Empresa Tercero | RUC | Num Personal | Fotocheck |
Empleado | DNI | Grupo Tercero | Sexo | Centro Costo | Fecha | Hora | Equipo |
Tipo Acceso | Tipo Marcadores | Situación | Motivo Bloqueo`

- `Tipo Acceso`: `Entrada` / `Salida` (heurística: "entrada"/"ingreso" → in).
- `Situación`: `Permitido` (y otras); se filtra/parametriza.
- Identificadores confiables: `DNI`, `Fotocheck`, `Num Personal`, `Empleado`.

### RELATORIO (maestro de personal) — hoja `Sheet1` (16 752 filas)
`Empresa | Unidad | Codigo del Grupo | Grupo Empresa | Codigo Empresa |
Empresa Terceros | RUC | Nombre Comercial | Grupo Terceros | Empleado |
Fotocheck | Fecha de Admisión | Fecha de Despido | Motivo Despido |
Fecha Inactividad | Motivo Inactividad | Inicio Actividad | Fin Actividad |
DNI | Extranjero | Sexo | Fecha Nacimiento | Cargo | Sección | Matrícula Ext |
Fecha Inclusión | Hora Inclusión | Contrato | Unidad de Trabajo | Perfil
Contrato | Tipo de Sangre`

- `Empleado` trae formato `000000002 - ALBERT RAMIREZ MEDINA` (código + nombre).
- Campos de alta/despido/inactividad permiten determinar ACTIVO/INACTIVO.

### TARIFAS (tarifario) — hoja `query (17)` (65 filas)
`ID | Title | Empresa | Objeto del contrato | RUC | Descripcion Cargo |
25% | 35% | 100% | Tipo de Item | Caminho`

- La tarifa se define por **Empresa + Objeto del contrato + RUC + Cargo** (NO
  solo cargo). Ej.: MAGNEX GROUP PERU/CJM, RUC 20492518311, "Ingeniero de
  Planeación y Programación" → 25 %=55.38 / 35 %=59.81 / 100 %=88.60.

### ÁREAS y GERENCIA (enriquecimiento opcional)
- ÁREAS: `Título | Id_Gerencia | Id | Tipo de Item | Caminho`.
- GERENCIA: `Título | Id | Tipo de Item | Caminho`.

---

## B. Relaciones entre archivos

```
RAINBOW ──(DNI/Fotocheck/NumPersonal/Empleado)──► RELATORIO (maestro personal)
RELATORIO ──(Empresa + RUC + Cargo + Contrato)──► TARIFAS (tarifa base)
ÁREAS ──(Id_Gerencia)──► GERENCIA ──(Título)──► análisis por gerencia/área
```

## C. Claves de relación

| Fuente | Clave primaria | Claves de unión |
|---|---|---|
| RAINBOW | `DNI`, `Fotocheck`, `Num Personal` | `DNI`, `Fotocheck`, `Num Personal`, `Empleado` (nombre) |
| RELATORIO | `DNI` / `Fotocheck` / código de `Empleado` | `DNI`, `Fotocheck`, código de `Empleado`, nombre |
| TARIFAS | `ID` | `Empresa` + `RUC` + `Cargo` (+ `Objeto del contrato`) |

## D. Reglas actuales (Asistencia Masiva)

1. Solo considera `Situación == Permitido`.
2. Agrupa marcaciones por Empleado y empareja Entrada→Salida con heurística de
   tiempo (si >14 h sin salida, asume nuevo ingreso).
3. Sanea tramos >24 h.
4. Genera 1 hoja Excel (Empresa, Empleado, Fecha/Hora inicio-fin, horas,
   horas hexagesimales) y alimenta un CSV para el dashboard nativo.
5. **No calcula horas extras, ni tarifa, ni monto, ni estados, ni auditoría.**

## E. Problemas encontrados

1. El módulo actual no valora la tarifa (no hay HH.EE. ni monto en soles).
2. Matching tarifario inexistente; tarifas sin asignar por Empresa/RUC/cargo.
3. Estado ACTIVO/INACTIVO del personal no se considera.
4. Sin auditoría trazable ni estados por registro (OK/ADVERTENCIA/REVISAR/ERROR).
5. Datos: TORNERO no tiene tarifa en TARIFAS → correcto marcarlo SIN_TARIFA, no
   inventar una tarifa.
6. El `horas_extras`/`Aplicativo_Rainbow.exe` se ejecutaba como binario externo
   en red (no disponible dentro del ejecutable) → se resuelve con plugin
   **embebido**.

## F. Nueva arquitectura

Ver `plugins/horas_extras_masiva/README.md`. Resumen: ingesta por capas con
configuración centralizada; motor reutilizable (CLI + widget + tests) dentro de
`engine/src`; GUI embebida vía `PluginRegistry.load_plugin_module` +
`create_widget()`; empaquetado de `plugins/` dentro del ejecutable.

## G. Algoritmo de cálculo

```
horas_trabajadas = fin - inicio           (Decimal, soporta cruce medianoche)
descuento_comida = según turno            (p. ej. T1: 1 h, sin comida si < 6 h)
jornada          = horas_trabajadas - descuento_comida
horas_extras     = max(0, jornada - jornada_contratada_del_turno)
```

## H. Algoritmo de matching tarifario

```
candidatos = tarifas cuyo Cargo ≈ cargo (exacto o difuso >= umbral)
ALTA  = candidatos con RUC == y Empresa == (y Objeto == si se exige)  -> 1 => ALTA
        (varios => ALTA AMBIGUA)
MEDIA = candidatos con Empresa == (sin RUC)  -> 1 => MEDIA (varios => ambigua)
BAJA  = solo cargo coincide           -> TARIFA AMBIGUA — REVISAR
ninguno                                -> SIN_TARIFA
```

## I. Estructura del Excel final (6 hojas)

`RESUMEN | DETALLE | AUDITORIA | ERRORES | TARIFAS | MARCACIONES`.

## J. Archivos Python a modificar / creados

Creados (nuevo plugin `horas_extras_masiva`):
`engine/src/{config,utiles,matching,ingesta,conciliacion,reglas,tarifario,validacion,dashboard,exportacion,motor,main}.py`,
`gui/widget.py`, `plugin.json`, `config/config.json`, `README.md`,
`tests/unit/test_horas_extras_masiva.py`.

Modificados para integrar y empaquetar:
- `NEXA_Productivity_Hub.spec` (bundle `plugins/`).
- `nexa_hub.spec` (hiddenimports del nuevo widget).
