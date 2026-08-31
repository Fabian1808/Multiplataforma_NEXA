# Horas Extras Masiva (plugin embebido)

Evolución del módulo **Asistencia Masiva (Rainbow)** hacia un cálculo formal de
**HORAS EXTRAS MASIVA**: entra la marcación RAINBOW, se concilia contra el
maestro de personal (RELATORIO), se valoriza contra el tarifario (TARIFAS) por
niveles de confianza y se exporta un Excel de 6 hojas. Corre **embebido dentro
del ejecutable del Hub** (plugin `execution_mode: embedded`), sin binarios
externos en red.

## Arquitectura (por capas)

```
plugins/horas_extras_masiva/
  plugin.json                 # embedded -> gui.widget
  engine/src/
    config.py                 # configuración centralizada (columnas, turnos, reglas, matching)
    utiles.py                 # normalización fechas/horas/nombres + dinero Decimal
    matching.py               # similitud difusa (token-set/sort) sin dependencias externas
    ingesta.py                # lectores: Rainbow, Relatorio, TARIFAS, Áreas, Gerencia
    datos_embebidos.py        # TARIFAS/ÁREAS/GERENCIA FIJOS embebidos en el motor
    conciliacion.py           # Rainbow <-> Personal (claves exactas + nombre difuso)
    reglas.py                 # turnos T1/T2/T3, jornada, horas extras
    tarifario.py              # matching tarifario + valorización 25/35/100 -> monto S/
    validacion.py             # estados OK/ADVERTENCIA/REVISAR/ERROR
    dashboard.py              # agregaciones y análisis TOP
    exportacion.py            # Excel de 6 hojas con estilo NEXA
    motor.py                  # orquestador del flujo completo
    main.py                   # CLI
    config/config.json        # ejemplo de configuración
  gui/widget.py               # widget Qt (embedded) con create_widget()
  tests/...                   # pruebas del motor
```

## Flujo

```
RAINBOW (marcaciones) ─┐
RELATORIO (maestro)   ─┼─► INGESTA ─► CONCILIACIÓN ─► JORNADAS/TURNOS ─►
TARIFAS/ÁREAS/GERENCIA ─┘        (embebidos en el motor)
                                                                       │
                                                                       ▼
   EXPORTACIÓN Excel (6 hojas) ◄── VALIDACIÓN (estados) ◄── VALORIZACIÓN (S/)
```

> **Nota**: el usuario solo necesita subir RAINBOW (uno o varios archivos) y
> RELATORIO. TARIFAS (tarifario), ÁREAS y GERENCIA están embebidos en
> `datos_embebidos.py`, por lo que no hace falta subirlos. Para actualizarlos,
> editar ese archivo (o pasar los archivos vía motor/fuentes).

## Reglas (todas parametrizables en config.py)

| Concepto | Regla predeterminada |
|---|---|
| Turnos | T1 (diurno, 10 h), T2 (noche, 12 h, cruza medianoche), T3 (tarde, 8 h) |
| Jornada | `horas_trabajadas - descuento_comida` |
| Horas extras | `horas_trabajadas - jornada_contratada` (solo si > 0) |
| Clasificación | SOBRETIEMPO (primeras 2 h a 25 %, exceso a 35 %) · ACTIVACIÓN (≥ 7 h a 100 %) |
| Moneda | `Decimal` exacto, 2 decimales, símbolo `S/` (sin errores de punto flotante) |

## Matching tarifario (por niveles de confianza)

- **ALTA**: Empresa + RUC + Cargo (y Objeto del contrato si `requiere_objeto`).
- **MEDIA**: Empresa + Cargo.
- **BAJA**: solo Cargo → marcada como **TARIFA AMBIGUA — REVISAR**.
- **SIN_TARIFA**: no hay tarifa para el cargo.
- Nunca se toma la primera fila del Excel ni se asume cargo=tarifa.

## Excel de salida (6 hojas)

`RESUMEN, DETALLE, AUDITORIA, ERRORES, TARIFAS, MARCACIONES` con encabezado
naranja NEXA (`#FF5503`), filtros y anchos automáticos.

## Uso

CLI:
```
python plugins/horas_extras_masiva/engine/src/main.py \
    --rainbow RAINBOW.xlsx --relatorio RELATORIO.xlsx --tarifas TARIFAS.xlsx \
    [-o salida.xlsx] [--config config.json]
```

GUI: desde el Hub, abrir el plugin **Horas Extras Masiva**, seleccionar los
archivos y pulsar **Calcular**. Exportación con el botón **Exportar Excel**.

## Pruebas

```
python -m pytest tests/unit/test_horas_extras_masiva.py -q
```
