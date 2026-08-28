# Arquitectura — NEXA Productivity Hub

## Visión general

Aplicación de escritorio **PySide6 (Qt6)** con la clásica trinidad vista/servicio/datos:

```text
hub/
├── app.py                 Entry point: splash, mutex single-instance, ícono, ServiceContainer
├── ui/                    Vista (Qt widgets)
│   ├── shell.py           Shell: header + sidebar + QStackedWidget n
│   ├── common/design.py   Sistema de diseño: tokens de tema, Icon() (SVG), NEXAStyles (QSS)
│   ├── auth/              Login
│   ├── dashboard/         Dashboard + dashboard mejorado
│   ├── catalog/ | search/ | reports/ | app_viewer/
│   └── admin/             Centro admin, auditorías, usuarios, solicitudes, KB, feed...
├── core/                  Servicios (ServiceContainer los cablea)
├── infrastructure/        database.py (sqlite thread-safe), logging_setup.py
├── models/                Dataclasses (User, PluginDescriptor, Request, Notification...)
├── plugins/               Herramientas embebidas con manifest plugin.json
├── modules/               Extensiones de plataforma (excel, outlook, pdf, sap)
└── tests/                 pytest
```

`hub\app.py` construye `ServiceContainer` e inyecta los servicios en el `Shell`,
las vistas acceden a los servicios que necesitan vía atributos del container.

## ServiceContainer (`hub/core/service_container.py`)

Crea y posee todos los servicios, con un `close()` ordenado (cierra workers y procesos):

| Servicio | Rol |
|---|---|
| `Database` | sqlite `nexus.db` con `_lock` para hilos |
| `AuthService` | login, roles (`usuario`/`creador`/`administrador`), usuarios |
| `AuditService` | registro de auditoría |
| `ConfigService` / `AppStateService` | configuración y estado por app |
| `PluginRegistry` / `CatalogService` | plugins embebidos + catálogo centralizado |
| `SearchEngine` | buscador global (apps, procesos, guías, soluciones) |
| `MetricsCollector` / `HealthCheckService` | métricas e health check de herramientas |
| `KnowledgeService` / `FeedService` | base de conocimiento y feed |
| `RequestService` | solicitudes de ayuda/automatización |
| `NotificationService` | notificaciones |
| `OpportunityTracker` | oportunidades detectadas |
| `ProjectService` / `WorkflowEngine` / `ReportService` | proyectos, workflows y reportes |
| `FavoritesService` | favoritos por usuario |
| `AppLauncherService` | **lanzador de herramientas externas** (ver abajo) |

## Modelo de plugins (`hub/models/plugin.py`)

`PluginDescriptor` describe cada herramienta:

- **Embebidas** (`is_external=False`): widgets en Python ejecutados dentro del Hub
  mediante `registry.get_factory(id) → create_widget()`. Ej: `plugins/horas_extras`,
  `plugins/sap_automation` (`plugin.json` con id/nombre/manifest).
- **Externas** (`is_external=True`): ejecutables independientes (`Horas Extras.exe`,
  `SAP.exe`, etc.) que no viven en el repo; se localizan por `launch_paths`
  (rutas locales o `smb://`) o `launch_url` (http/https), se copian a la carpeta
  local de apps y se lanzan con `QProcess`.

## Launcher externo (`hub/core/app_launcher_service.py`)

- `launch(plugin)`: localiza binario → si falta, `install(block=True)` (descarga
  con espera acotada ~25 s, sin congelar la UI) → lanza con `QProcess`
  reutilizando la instancia ya abierta.
- `install_async(plugin)`: descarga en `_DownloadWorker` (QThread) con timeout de
  red (15 s), emite `install_finished(plugin_id, ok, mensaje)` en el hilo de UI.
- `AppViewer._launch_external()` (`hub/ui/app_viewer/app_viewer.py`): si el binario
  no está instalado, informa al usuario, arranca `install_async` y, cuando termina
  (`_on_install_finished`), abre la herramienta o muestra el error.
- `close()`: interrumpe workers y mata procesos vivos al salir.
- Fuentes soportadas: ruta local (`C:\...`/UNC), `smb://host/...` (se convierte a
  `\\host\...`), `file://` y `http(s)://` (vía `urllib.request`, extremo con
  tamaño > 0 y limpia de accesos temporales).

## Base de datos (`hub/infrastructure/database.py`)

SQLite en `%APPDATA%\NEXA\ProductivityHub\data\nexus.db`.

- **Thread-safe**: todas las operaciones se serializan con `self._lock`.
- `close()` con el lock **y con guardado idempotente** (fix de crash nativo
  0xC0000005 al cerrar mientras un worker en background consulta la BD).
- `SELECT`/`INSERT`/`UPDATE`/`DELETE` helper para las consultas de los servicios.

## Hilos y ciclo de vida

Evitar tocar widgets desde hilos que no son el de la UI:

- `_DownloadWorker` (QThread) hace red/copia de archivos y comunica vía `Signal`.
- El shell refresca el fondo del dashboard con un worker que consulta la BD
  (`showEvent` → `_refresh_dashboard_bg`).
- Al cerrar: `Shell._disconnect_all()` + `ServiceContainer.close()` drena workers
  y mata procesos externos antes de liberar la conexión.