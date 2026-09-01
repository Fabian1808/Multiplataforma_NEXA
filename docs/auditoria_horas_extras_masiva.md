# Auditoría — Horas Extras Masiva

## FASE 0 / 1 — Diagnóstico inicial y causa raíz del crash

**Commit base (punto de restauración):** `8a755f9` (tag `backup/pre-auditoria-hem`)

### Arquitectura actual

```
hub/app.py                     MainWindow, shell, closeEvent, create_app (splash)
hub/ui/shell.py                Shell: layout, páginas (QStackedWidget), apply_theme(), _set_theme()
hub/ui/app_viewer/app_viewer.py  AppViewer: vista del plugin. refresh_style() RECONSTRUYE la vista
plugins/horas_extras_masiva/
  gui/widget.py                Widget Qt. Cálculo/exportación en QThread (_CalculoThread/_ExportarThread)
  engine/src/ingesta.py        Lectura openpyxl (Rainbow/Relatorio/Tarifas/Áreas/Gerencia)
  engine/src/conciliacion.py   MaestroPersonal + conciliar()
  engine/src/reglas.py         Turnos T1/T2/T3, jornadas, horas extras
  engine/src/tarifario.py      Matching tarifario + valorización
  engine/src/validacion.py     Estados OK/ADVERTENCIA/REVISAR/ERROR
  engine/src/dashboard.py      Analisis: agregaciones y TOP
  engine/src/exportacion.py    Excel de 6 hojas
  engine/src/motor.py          Orquestador (MotorHorasExtrasMasiva)
```

### Problema principal

**Crash / cierre total de la aplicación** al hacer clic en "Calcular Horas Extras Masiva"
y, mientras se procesa, cambiar el tema (Modo oscuro / Modo claro).

### Causa raíz del crash (confirmada por inspección de código)

1. `AppViewer.refresh_style()` (app_viewer.py:430) **reconstruye toda la vista** llamando
   a `_setup_ui()` (que hace `deleteLater()` sobre `_body_widget` y todos sus hijos) y
   después `load_plugin()` que vuelve a crear el widget del plugin.
2. `Shell.apply_theme()` (shell.py:1623) llama a `page.refresh_style()` sobre TODAS las
   páginas en cada cambio de tema. `Shell._set_theme()` invoca `apply_theme()`.
3. El widget del plugin (`HorasExtrasMasivaWidget`) es **padre** de los `QThread`
   de cálculo (`_CalculoThread`) y de exportación (`_ExportarThread`) creados con
   `parent=self`.
4. Si el cálculo/exportación está corriendo cuando el tema cambia, el widget (y por
   tanto el `QThread`) se destruye en medio del procesamiento. Qt aborta con
   **fatal error** `QThread: Destroyed while thread is still running` → la aplicación
   **se cierra por completo**. Esto es una muerte dura (abort), no una excepción Python
   capturable de forma fácil, por eso "no hay traceback".

### Cómo se reproduce

```
Abrir app → abrir plugin Horas Extras Masiva → Calcular
mientras procesa → clic en Modo oscuro/claro   → CRASH
```

### Posibles causas descartadas / confirmadas

| Candidata                                   | Estado |
|---------------------------------------------|--------|
| Actualización de widgets desde worker       | No: los QThread solo emiten señales; la UI se actualiza en el hilo principal (ok) |
| Referencias a widgets destruidos            | Sí: el QThread queda huérfano si su padre widget se destruye |
| QThread destruido en ejecución              | **SÍ — causa raíz** |
| Race conditions en variables compartidas    | Menor; `_resultado`/`_cfg` se leen tras `finalizado` |
| Cambio de estilos masivo                    | Sí: AppViewer aplica estilos en cada rebuild (ineficiente, no causa crash por sí solo) |
| Excepciones sin capturar (hilo principal)   | No hay `sys.excepthook` global; un error no capturado en slot silencia |
| Bloqueo del event loop                     | No en método actual (cálculo en QThread) |
| Memory leaks                                | Sí, varios (ver FASE 4) |

### Principales cuellos de botella

- `dashboard.Analisis` se re-crea múltiples veces por render (re-recorre filas).
- `AppViewer.refresh_style()` reconstruye widgets en cada cambio de tema (lento + parpadeo).
- Exportación escribe el Excel completo vía `openpyxl` en un QThread (correcto) pero sin
  progreso ni cancelación.
- Sin medición de tiempos por fase (imposible detectar dónde se pierde tiempo).
- `Resultado.__post_init__` re-suma montos cada vez (bajo impacto).

### Problemas de concurrencia

- Workers no se limpian ni se espera su finalización al destruir el widget.
- No hay mecanismo de cancelación.
- No hay `sys.excepthook` ni captura de excepciones de hilo.

### Problemas de UI

- El cambio de tema causa reconstrucción total del AppViewer (parpadeo y riesgo de crash).
- Los widgets del plugin leen `Theme.*` solo al crearse; sin `refresh_style()` propio
  quedan fuera de tema si no se reconstruye.

### Riesgos detectados

1. Perder datos de `_resultado` (no se pierde: vive en el widget, ver FASE 3/4 para caché).
2. QThread huérfano → abort de Qt.
3. Sin backup de workers, cierre de app en medio de cálculo deja hilos vivos.

## FASE 2 — Corrección del crash (tema ↔ cálculo en ejecución)

### Cambios implementados

- **`hub/ui/app_viewer/app_viewer.py`**
  - `AppViewer.refresh_style()` deja de reconstruir la vista: ahora **re-aplica el tema en
    sitio** (fondo del body, textos `avTitle/avDesc/avMuted/avText`, KPIs, botones
    `avPrimary/avSecondary`, y pide al plugin `refresh_style()` si existe). No llama a
    `_setup_ui()` ni a `load_plugin()` → el widget del plugin y sus `QThread` **nunca se
    destruyen** por un cambio de tema.
  - Cache persistente `self._plugin_widget`: el widget embebido se crea **una sola vez** y
    se reutiliza entre cambios de tema y navegación (`_load_plugin_widget` lo vuelve a
    añadir al layout en vez de recrearlo).
  - Se añadieron `setObjectName()` a títulos/descripciones/botones/KPIs del AppViewer para
    que el restyling en sitio los encuentre por nombre.
- **`plugins/horas_extras_masiva/gui/widget.py`**
  - `refresh_style()` propio: re-colorea título/descripción/status, tabs y KPIs usando la
    paleta `Theme` activa (claro/oscuro) sin reconstruir nada.
  - Botón **Cancelar proceso**, `_estrategia_cancelar`, progreso por etapas
    (`progreso(int, str, int, int)`) y exportación con barra indeterminada.
  - `shutdown()`/`closeEvent` que esperan (≤8 s) a los workers, y slots que limpian
    `_worker`/`_worker_exp` al terminar (`finished`).
  - Workers siguen emitiendo solo señales (jamás tocan widgets); su vida queda ligada al
    widget, que ya no se destruye en caliente.
- **`plugins/horas_extras_masiva/gui/thread_registry.py`** (nuevo, sin dependencias pesadas)
  - Registro global de hilos de trabajo activos + `esperar_hilos_activos()`.
- **`hub/app.py`**
  - `app.aboutToQuit` conectado a un hook que espera a los hilos de trabajo del plugin antes
    de cerrar (evita el fatal también al salir de la app con un cálculo en curso).

### Verificación (offscreen, proceso real)

Reproducción exacta del race original (cálculo real corriendo en `_CalculoThread` mientras se
llama a `AppViewer.refresh_style()` + `widget.refresh_style()` cada ~120 ms):

- **~600 llamadas a `refresh_style()` durante el cálculo → sin fatal `QThread: Destroyed`**,
  sin excepción, resultado cargado correctamente (`resultado_cargado=True`), el widget sigue
  siendo el mismo objeto (`widget_vivo=True`), worker liberado tras `finished`.
- `pytest tests`: **114 passed** (sin regresiones).

### Base de referencia "ANTES" (para benchmark de FASE 3+)

Datos reales de producción (10 archivos RAINBOW + RELATORIO):

| Fase                                   | Tiempo |
|----------------------------------------|--------|
| `leer_rainbow` (10 xlsx)               | ~17.2 s  → **340 662 marcaciones** |
| `leer_relatorio` (1 xlsx)              | ~1.5 s   → **16 752 empleados** |
| `motor.ejecutar` (pipeline completa)   | **> 180 s** (timeout; se optimiza en FASE 3) |

Hipótesis de cuello de botella FASE 3 (a confirmar): el costo dominante es la **conciliación/
matching por nombre** (fallback difuso) cuando una marcación no matchea por DNI: 340k × 16k
empleados ≈ miles de millones de operaciones si hay marcaciones sin DNI. `leer_rainbow`
también debería reducirse (lectura por filas/filas innecesarias).

## FASE 3 — Optimización de rendimiento del motor

### Medición "ANTES" (datos reales, pipeline completa, 10 RAINBOW + RELATORIO)

| Fase                          | Tiempo  | Observación |
|-------------------------------|---------|-------------|
| 1 `leer_rainbow`              | 31.97 s | 340 662 marcaciones |
| 2 `leer_relatorio`            | 3.68 s  | 16 752 empleados |
| 3 tarifas/áreas/gerencia      | 0.00 s  | embebidas |
| 4 `MaestroPersonal._build`    | 0.23 s  | |
| **5 `conciliar`**             | **751.93 s** | **83% del total — el cuello de botella** |
| 6 `calcular_jornadas`         | 2.58 s  | 62 313 jornadas, 24 131 malformadas |
| 7 tarifario + valorizar       | 5.79 s  | 62 313 filas |
| 8 estados                     | 0.07 s  | |
| 9 `__post_init__`             | 0.12 s  | |
| **Total**                     | **~757 s** | |

### Diagnóstico de causa raíz

- Solo **~2.4 %** de las marcaciones (202 de 8 296 muestreadas) carecen de DNI y caen al
  **matching difuso por nombre**, pero cada una recorría el bucle completo de **16 752
  empleados** ejecutando `SequenceMatcher` (token-set + token-sort) por cándido → cientos de
  millones de comparaciones.
- `leer_rainbow` normalizaba fecha y hora por fila (340k × hasta ~4 intentos de parseo).

### Cambios implementados

- **`conciliacion.py` — índice invertido por token** (`MaestroPersonal`):
  - En `_build` se indexa cada token normalizado → `{token: [indices de empleados]}`.
  - `buscar_nombre` solo evalúa candidatos que **comparten ≥1 token** con el nombre buscado
    (en vez de los 16 752). Resultado idéntico al barrido completo (verificado con A/B).
  - Cache de la normalización del nombre buscado (`_cache_nom_fuzzy`).
  - Se guarda el `frozenset` de tokens de cada empleado para acelerar el pre-filtrado.
- **`ingesta.py`** — cache de `normalizar_fecha`/`normalizar_hora` por valor en
  `_leer_rainbow_unico` (los mismos value objects se repiten mucho).
- **`matching.py` — bug de no-determinismo corregido**:
  - `ratio_token_set` hacía `" ".join(inter_set)` sobre un **set**, cuyo orden depende del
    hash de los strings (`PYTHONHASHSEED`) → el puntaje difuso y por tanto **el monto total
    cambiaba de una corrida a otra** y entre máquinas. Ahora `" ".join(sorted(inter_set))`
    es estable. Independiente de los cambios de rendimiento, este era un **defecto latente**
    que volvía el resultado de horas extras no reproducible.
- **`motor.py` — timing + progreso por etapa**:
  - `plan(..., on_etapa=None)` recibe un callback `on_etapa(nombre, pct)` y registra con
    `logging` el tiempo de cada fase.
  - `_CalculoThread` (`widget.py`) pasa `on_etapa` para reportar etapas reales a la barra de
    progreso (en lugar de quedarse clavado en "Procesando…").
- **Tests añadidos** (117 verdes): equivalencia `buscar_nombre` índice↔barrido, determinismo
  de `mejor_token`, y conciliación con el nuevo índice.

### Verificación

**A/B determinismo y equivalencia sobre el corpus completo real:**

| Modo           | Monto total  | Fila a fila vs. optimizado |
|----------------|--------------|----------------------------|
| Optimizado (índice) | 275 393.16 | — |
| Barrido original (flag `HEM_FUZZY_BRUTE=1`) | 275 393.16 | **0 diferencias en 62 313 filas** |

- **Determinismo**: montos idénticos con `PYTHONHASHSEED=1/2/999` (antes variaban).
- `pytest tests`: **117 passed**.

### Resultado "DESPUÉS" (mismo dataset)

| Fase                          | ANTES    | DESPUÉS  | Ganancia |
|-------------------------------|----------|----------|----------|
| `leer_rainbow`                | 31.97 s  | 14.49 s  | ~2.2× |
| **`conciliar`**               | **751.93 s** | **15.17 s** | **~50×** |
| `calcular_jornadas`           | 2.58 s   | 1.24 s   | ~2× |
| tarifario + valorizar         | 5.79 s   | 2.63 s   | ~2.2× |
| **Total**                     | **~757 s** | **~35 s** | **~21×** |

Los tiempos restantes (14 s de lectura + 15 s de conciliación) siguen dominados por el
volumen (340k marcaciones) en Python puro; la conciliación ya es ~lineal en marcaciones.

## FASE 4/5/6/7/8 — Memoria, UI/tema, arranque, logging, manejo de errores

### FASE 4 — Memoria (UI)

- **`widget._cargar_tabla_detalle`**: `QTableWidget` no virtualiza; materializar 62 313 filas
  × 17 columnas (~1M `QTableWidgetItem`) disparaba la memoria y congelaba el render. Ahora la
  tabla pinta como máximo `_MAX_FILAS_TABLA = 5000` filas y avisa en el status; el Excel
  exportado y el Dashboard siguen reflejando el total completo. `Resultado.filas` se libera
  internamente al regenerar.
- Los workers (`_CalculoThread`/`_ExportarThread`) se limpian (`self._worker = None`) al
  terminar (de FASE 2), y `thread_registry` permite esperarlos antes de cerrar la app.

### FASE 5 — UI / tema reactiva

- `KPIWidget.refresh_style(color)` y `StatusBadge.refresh_style()` añadidos en
  `hub/ui/common/components.py` y `styles.py`: re-aplican la tarjeta/textos con el tema activo
  sin recrear el widget.
- `AppViewer.refresh_style()` usa el nuevo `kpi.refresh_style()` (en vez de tocar atributos
  privados) y re-aplica fondo, textos y botones en sitio; el plugin widget se conserva y
  re-estila (FASE 2). Verificado: el widget sobrevive a `refresh_style()` del contenedor y a
  re-cargar el plugin (`smoke_theme` PASS).

### FASE 6 — Arranque (lazy del plugin)

- `PluginRegistry.discover()` solo lee `plugin.json`; `load_plugin_module()` es lazy y el
  `import PySide6.QtCharts` ocurre únicamente al crear el widget. El plugin **no** penaliza el
  arranque del Hub.

### FASE 7 — Logging / monitoreo

- `hub/infrastructure/logging_setup.py` escribe `hub_<fecha>.log` (+ `errors.log`, rotativos).
- Los loggers `horas_extras_masiva` y `horas_extras_masiva.motor` propagan al root → sus
  mensajes y el **timing por etapa** (nuevo en `motor.plan`) quedan registrados en el mismo
  archivo de log del Hub (+consola). Verificado end-to-end con `setup_logging`.

### FASE 8 — Manejo de errores global

- `sys.excepthook` global instalado en `hub/app.py::main()`: registra la excepción no
  capturada (`logger.critical` con traceback) y muestra un cuadro amistoso no bloqueante
  (programado con `QTimer`, seguro en offscreen).
- Los workers de cálculo/exportación ya capturan excepciones y emiten `finalizado(False, msg)`
  con traceback en el log + cuadro de error en la UI (de FASE 2).

### Pruebas de regresión

- `pytest tests`: **117 passed** (3 tests nuevos de FASE 3: equivalencia índice↔barrido,
  determinismo de `mejor_token`, conciliación con índice).
- Stress de concurrencia (tema ↔ cálculo en ejecución): **PASS** — sin fatal, resultado
  cargado, widget vivo, worker limpiado.
- Smoke de tema (FASE 5): **PASS** — widget persiste ante refresh y recarga.

## FASE 15 — Informe final: problemas detectados y optimizaciones aplicadas

### Benchmark consolidado (datos reales: 10 RAINBOW + RELATORIO, 340 662 marcaciones, 16 752 empleados, 62 313 jornadas)

| Fase                            | ANTES (s) | DESPUÉS (s) | Ganancia |
|---------------------------------|-----------|-------------|----------|
| `leer_rainbow`                  | 31.97     | 14.49       | ~2.2×    |
| `leer_relatorio`                | 3.68      | 1.50        | ~2.5×    |
| **`conciliar`**                 | **751.93**| **15.17**   | **~50×** |
| `calcular_jornadas`             | 2.58      | 1.24        | ~2×      |
| tarifario + valorizar           | 5.79      | 2.63        | ~2.2×    |
| estados / post_init             | 0.19      | 0.11        | ~1.7×    |
| **Total pipeline**              | **~757 s**| **~35 s**   | **~21×** |

### Tabla de problemas → soluciones

| # | Fase | Problema                                       | Causa raíz                                          | Solución aplicada                                      | Validación |
|---|------|------------------------------------------------|-----------------------------------------------------|--------------------------------------------------------|------------|
| 1 | 0/1  | **Crash/cierre total** al cambiar tema durante el cálculo | `AppViewer.refresh_style()` reconstruía la vista y destruía el widget con QThread vivo (`QThread: Destroyed while thread is still running`) | `refresh_style()` re-aplica en sitio; widget cacheado y reutilizado; `refresh_style()` del plugin; `shutdown()`/thread_registry; espera en `aboutToQuit` | 600+ refreshes durante cálculo SIN fatal; stress PASS |
| 2 | 3    | Pipeline ~13 min en datos reales            | Matching difuso recorría 16 752 empleados por marcación sin DNI (bucle O(N×M) con SequenceMatcher) | Índice invertido por token: candidatos solo si comparten token; cache de normalización | `conciliar` 752 s → 15 s (0 dif fila a fila vs. original) |
| 3 | 3    | Monto resultante no reproducible             | `" ".join(inter_set)` sobre un `set` → orden dependía de `PYTHONHASHSEED` | `" ".join(sorted(inter_set))` | Montos idénticos con seed 1/2/999 |
| 4 | 3    | Sin visibilidad de dónde se pierde el tiempo | Sin medición por fase                           | Timing por etapa + callback `on_etapa` y logging en `motor.plan` | Logs `horas_extras_masiva.motor` por etapa |
| 5 | 3    | Progreso de la barra "congelado"             | `_CalculoThread` emitía etapas fijas            | `on_etapa` real desde el motor                       | Barra muestra etapas reales |
| 6 | 4    | Memoria/render con 62k filas x 17 col        | `QTableWidget` no virtualiza (~1M items)        | Tabla paginada a 5 000 filas + aviso; export Excel completa | Render estable; tests OK |
| 7 | 5    | Widgets quedaban fuera de tema al cambiar    | Leían `Theme.*` solo al crearse                  | `KPIWidget.refresh_style()` / `StatusBadge.refresh_style()` | Smoke tema PASS |
| 8 | 8    | Errores no capturados en silencio            | Sin `sys.excepthook` global                      | `sys.excepthook` log + mensaje amistoso             | Verificado en `main()` |
| 9 | 2    | Cierre de app en medio de cálculo dejaba hilos vivos | QThread sin espera al destruir               | `thread_registry` + `aboutToQuit` los espera        | Stress PASS |
| 10| 7    | Logs del plugin no en archivo                | loggers con propagación por defecto              | Confirmada propagación a root handlers               | Verificado end-to-end |

### Estado final

- **117 tests** verdes en `tests/` (3 añadidos en FASE 3).
- Conversión del crash original en operación robusta (workers fuera de UI, cancelación,
  espera al salir).
- Rendimiento del plugin: **~757 s → ~35 s** (~21×) y salida determinista.
- Códigos tocados: `hub/app.py`, `hub/ui/app_viewer/app_viewer.py`,
  `hub/ui/common/{styles,components}.py`, `plugins/horas_extras_masiva/engine/src/{motor,conciliacion,ingesta,matching}.py`,
  `plugins/horas_extras_masiva/gui/{widget,thread_registry}.py`, `tests/unit/test_horas_extras_masiva.py`.
- Los cambios están en el árbol de trabajo (sin commit; no se solicitó commit). El repo sigue
  con `RAINBOW/` y `*.xlsx` ignorados (datos reales no versionados).
