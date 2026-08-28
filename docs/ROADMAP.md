# Roadmap y estado del producto

**Versión del paquete:** `2.0.0` (`hub/__init__.py`).
**Últimos entregables:** rediseño corporativo del sidebar + validación completa.

## Completado y verificado

### Fase 0 — Auditoría e infraestructura

- Repositorio inicializado en GitHub (`github.com/Fabian1808/Multiplataforma_NEXA`),
  rama `main`.
- Scripts de instalación/arranque/limpieza (`*.bat`) y spec de PyInstaller.
- Suite de tests: **86 tests `pytest` verdes** + smoke de GUI.

### Fase 1 — MVP (núcleo)

- Shell con sidebar, cabecera y navegación por páginas (`hub/ui/shell.py`).
- Login y roles (`usuario`/`gestor`/`administrador`), panel admin.
- Dashboard, Catálogo, Búsqueda global, AppViewer (plugins embebidos y externos).
- Logs estructurados, configuración, base de datos SQLite thread-safe.
- **Rediseño corporativo del sidebar** (ver `docs/DISENO.md`):
  - Paleta exacta claro/oscuro con tokens y persistencia (`theme.json`).
  - Navegación por secciones, ítems animados (160 ms hover/activo, colapso 220 ms),
    brand row con logo en tarjeta, píldora de tema, perfil, sección admin.
  - **Validación**: 25/25 checks de píxeles/geometría en offscreen + navegación
    de las 12 páginas en claro y oscuro con colapso/expansión.
- Parser SVG de iconos ampliado (arcos elípticos y repeticiones implícitas);
  inventario de 51 iconos outline, 22 en uso, sin faltantes ni emojis.
- Ícono de ventana/taskbar desde `assets/` y empaquetado con assets + `.ico`.
- Lanzador externo asíncrono (`AppLauncherService`) con descarga en segundo plano
  y aviso al terminar.
- Fix de crash nativo al cerrar (lock en `Database.close()`).

## Deuda técnica y pendientes (para continuar en casa)

### P0 — Verificación en el equipo real

1. **Probar el lanzador externo con un binario real.** `Horas Extras`/`SAP`
   apuntan a `\\SERVIDOR-NEXA\...` (rutas de red sin binarios accesibles desde
   este equipo). Para validar el flujo completo de `AppLauncherService`
   (descarga → `install_finished` → `QProcess`), registrar un plugin externo de
   prueba con un `.exe` local (p. ej. `notepad.exe`) y ejecutar desde
   `Aplicaciones`.
2. **Prueba visual real (con monitor)** con la app a mano: transiciones hover
   en vivo, colapso por el botón `panel-left`, redimensionado responsive e
   integración de las 12 páginas en ambos temas (los checks offscreen cubren
   píxeles/geometría, no el render en vivo).

### P1 — Limpieza y consistencia

3. Decidir el destino de los restos no versionados:
   - `Diagnostico_NEXA.bat`, `diag_wrapper.py`, `diag_exit.txt` (artefactos de
     diagnóstico; están en `.gitignore`, se pueden borrar en local).
   - `logo con nombre.png`, `logo para acceso directo.png` (fuentes originales;
     ya hay copias en `assets/`, en `.gitignore` para no duplicar espacio).
4. `nexa_hub.spec` quedó como spec antiguo (sin `assets`); el build oficial usa
   `NEXA_Productivity_Hub.spec`. Eliminar el duplicado o mantenerlo documentado.
5. Revisar `plugins/_template` y `plugins/horas_extras|sap_automation` para que
   expongan métricas de ejecución/health consistentes con `CatalogService`.

### P2 — Siguientes fases del prompt maestro

6. **Fase 2** (parcialmente hecha): valoraciones/rating, impacto por herramienta,
   cierre del flujo "solicitar ayuda / proponer automatización" en UI admin.
7. **Fase 3**: workflows encadenados, recetas, ejecuciones programadas,
   marketplace interno.
8. **Fase 4**: actualizaciones automáticas, health checks avanzados, analytics.
9. **Fase 5 / IA**: asistente NEXA (búsqueda semántica). **No empezar antes de
   tener base sólida** (regla del prompt maestro).

## Referencia (prompt maestro)

La especificación completa del producto (83 secciones: visión, UX, catálogo,
roles, seguridad, fases, definición de done, métricas North Star)
está en [`docs/PROMPT_MAESTRO.md`](PROMPT_MAESTRO.md). Trabajar siempre de cara
a su Fase 1 → Fase 5 y a la regla final:

> *"Si existe una forma más rápida de hacer una tarea dentro de NEXA, el
> trabajador debería poder encontrarla en menos de 30 segundos."*