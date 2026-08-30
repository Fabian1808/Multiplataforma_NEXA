# NEXA Productivity Hub

Plataforma interna de productividad para NEXA. Un único punto donde el trabajador
busca cómo hacer una tarea, encuentra una herramienta existente, ejecuta una
automatización, consulta una guía, pide ayuda o propone una nueva solución.

> **North Star:** *"Si existe una forma más rápida de hacer una tarea dentro de
> NEXA, el trabajador debería poder encontrarla en menos de 30 segundos."*

---

## Estado actual

- GUI de escritorio con **PySide6 (PySide6 ≥ 6.8)** y temas claro/oscuro persistente.
- **Sidebar corporativo rediseñado** con navegación por secciones, iconos lineales
  propios (familia Lucide outline), animaciones y colapso responsive. Ver
  [`docs/DISENO.md`](docs/DISENO.md).
- **12 páginas** navegables desde el sidebar (Dashboard, Catálogo, Búsqueda,
  Aplicaciones, Propuestas, Solicitudes, Incidencias, Conocimiento, Comunidad,
  Reportes, Auditoría y Gestión de Usuarios). Ver [`docs/DISENO.md`](docs/DISENO.md).
- Lanzador de herramientas externas (ejecutables independientes) con descarga
  en segundo plano desde recursos locales/compartidos. Ver
  [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md).
- **86 tests** verificados con `pytest`.

## Inicio rápido en Windows

```bat
:: 0) Launcher unificado (instala si es necesario y abre la app)
NEXA.bat

:: 1) Instalar (crea .venv e instala dependencias)
Instalar_NEXA.bat

:: 2) Abrir la aplicación
Iniciar_NEXA.bat

:: 3) Manual
.venv\Scripts\python.exe -m hub.app

:: 4) Tests
.venv\Scripts\python.exe -m pytest -q   (86 passed)

:: 5) Compilar ejecutable
Construir_Ejecutable.bat                 (usa NEXA_Productivity_Hub.spec)
```

Requiere **Python 3.11+** en el PATH.

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/DESARROLLO.md`](docs/DESARROLLO.md) | Instalación, ejecución, tests, compilación, rutas en disco, operación. |
| [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) | Capas, servicios, modelo de plugins, launcher externo, base de datos. |
| [`docs/DISENO.md`](docs/DISENO.md) | Sistema de diseño: paleta corporativa, iconos, sidebar, temas claro/oscuro. |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Estado del producto, deuda técnica y próximos pasos pendientes. |
| [`docs/PROMPT_MAESTRO.md`](docs/PROMPT_MAESTRO.md) | Especificación original del producto (prompt maestro), versión UTF-8. |

## Estructura del repositorio

```text
hub/
  app.py                 Entry point (splash, single-instance, ícono de app)
  ui/                    Vistas (shell, login, dashboard, catalog, search,
                         reports, admin/*, app_viewer/*, common/design.py)
  core/                  Servicios (auth, catalog, search, requests, audit,
                         notifications, workflow, reports, app_launcher...)
  infrastructure/        database.py (sqlite con lock), logging_setup.py
  models/                Dataclasses (user, plugin, request, notification...)
plugins/                 Herramientas embebidas (horas_extras, asistencia_masiva,
                         dashboard_hhee, sap_automation, _template)
modules/                Integraciones de lenguaje/plataforma (excel, outlook, pdf, sap)
tests/                   pytest (unit, smoke, integration)
assets/                  logos oficiales (logo_brand.png, logo_taskbar.{png,ico})
NEXA_Productivity_Hub.spec  Spec de PyInstaller (incluye assets e ícono)
*.bat                    Instalar / Iniciar / Construir / Limpiar
```

## Notas de operación

- Base de datos SQLite en `%APPDATA%\NEXA\ProductivityHub\data\nexus.db`.
- Preferencia de tema en `%APPDATA%\NEXA\ProductivityHub\theme.json`.
- Logs en `%APPDATA%\NEXA\ProductivityHub\logs\`.
- Herramientas externas descargadas en `%APPDATA%\NEXA\ProductivityHub\apps\`.
- Una sola instancia activa (mutex); al abrir una segunda se muestra un aviso.