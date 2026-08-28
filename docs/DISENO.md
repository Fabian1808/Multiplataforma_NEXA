# Sistema de Diseño — Sidebar NEXA

Documento de referencia del rediseño corporativo del sidebar de **NEXA Productivity
Hub**. Todo el código vive en:

- `hub/ui/common/design.py` — tokens de tema, `Icon()` (render de SVG propio),
  `NEXAStyles` (generadores QSS), estado global del tema.
- `hub/ui/shell.py` — `Shell` (header + sidebar + páginas), `_NavItem`.

## Identidad corporativa

Colores institucionales (se usan como **acento**, no como relleno de la UI):

```text
#FF5503   naranja NEXA (acción/acento)
#3B3B3B   gris oscuro (texto/iconos neutros)
#FFFFFF   blanco (superficies)
```

## Tokens de tema

`Theme.<token>()` devuelve el valor del tema activo en el momento de la llamada
(`t(light, dark)`). El modo se persiste en `%APPDATA%\NEXA\ProductivityHub\theme.json`.

### Acordes base

| Token | Claro | Oscuro |
|---|---|---|
| `bg` | `#F5F5F7` | `#111111` |
| `surface` | `#FFFFFF` | `#1C1C1F` |
| `card` | `#FFFFFF` | `#28282C` |
| `card_elevated` | `#F9F9FB` | `#2E2E34` |
| `sidebar_bg` | `#FFFFFF` | `#171717` |
| `header_bg` | `#FFFFFF` | `#202024` |
| `border` / `border_strong` | `#E5E5EA` / `#C7C7CC` | `#38383E` / `#4A4A52` |
| `text` | `#1C1C1E` | `#F2F2F7` |
| `text_secondary` | `#636366` | `#9A9AA8` |
| `text_muted` | `#AEAEB2` | `#5E5E6A` |
| `input_bg` | `#F5F5F7` | `#1C1C1F` |
| `hover_bg` | `#F0F0F3` | `#2E2E34` |
| `active_bg` | `#FFF2EC` | `#FF550318` |
| `section_label` | `#AEAEB2` | `#5E5E6A` |

### Paleta dedicada del sidebar

| Token | Claro | Oscuro |
|---|---|---|
| `sidebar_text` | `#1F1F1F` | `#F5F5F5` |
| `sidebar_text_secondary` | `#6B7280` | `#A3A3A3` |
| `sidebar_icon` | `#3B3B3B` | `#D4D4D4` |
| `sidebar_hover` | `#FFF1EB` | `#292929` |
| `sidebar_active_bg` | `#FFF3ED` | `#2A1A14` |
| `sidebar_border` | `#E5E7EB` | `#2D2D2D` |
| `sidebar_active` (acento) | `#FF5503` | `#FF6A2A` |
| `sidebar_card` (panel interno) | `#F7F8FA` | `#1E1E1E` |
| `logo_card_border` | `#E5E7EB` | `#3A3A3A` |

### Estados

```text
SUCCESS #16A34A   WARNING #D97706   ERROR #DC2626   INFO #2563EB
ACCENT  #FF5503   ACCENT_HOVER #E64C02   ACCENT_PRESSED #CC4402
```

## Tipografía y geometría

- `FONT_FAMILY = "Segoe UI"`, `get_font(size, weight, ...)`.
- UI instrucciones del diseño general: `CARD_RADIUS = 12`, `BUTTON_RADIUS = 8`,
  `HEADER_HEIGHT = 56`, `SIDEBAR_WIDTH = 256`, `SIDEBAR_COLLAPSED_WIDTH = 72`.

## Iconos (familia lineal propia)

- `Icon(name, px)` en `design.py` pinta SVG **outline** en el grid Lucide 24×24
  (stroke fino ≈1.8–2). **Sin emojis**: todas las vistas usan iconos de esta familia.
- El parser soporta `M/L/H/V/C/S/Q/T/A` (absolutos y relativos, repeticiones
  implícitas de comandos e incluso arcos elípticos → Béziers cúbicos,
  `_arc_cubics()`).
- Inventario actual: **51 iconos definidos** en `_PATHS`, **22 usados** por las
  vistas. Algunos del inventario: `house`, `layout-grid`, `search`, `app-window`,
  `lightbulb`, `clipboard-list`, `triangle-alert`, `book-open`, `users-round`,
  `chart-column`, `shield-check`, `user-cog`, `panel-left`, `sun`, `moon`,
  `bell`, `settings`, `logout`, `star`, `clock`, `download`, `external-link`, etc.

## Sidebar (`hub/ui/shell.py`)

### Estructura vertical

```text
┌─────────────────────────────┐
│ BRAND ROW  (logo en tarjeta │  56 px
│            blanca + colapsar) │
├─────────────────────────────┤
│ PRINCIPAL<section label>    │
│   house  Inicio             │
│   layout-grid  Catálogo     │
│   search  Búsqueda          │
│ GESTIÓN                    │
│   app-window  Aplicaciones  │
│   lightbulb  Propuestas     │
│   clipboard-list Solicitudes│
│   triangle-alert Incidencias│
│ CONOCIMIENTO               │
│   book-open  Conocimiento   │
│   users-round  Comunidad    │
│ ANALÍTICA                  │
│   chart-column  Reportes    │
│   shield-check  Auditoría   │
│ ADMINISTRACIÓN (solo admin) │
│   user-cog  Gestión Usuarios│
│            ⋮ (stretch)      │
├─────────────────────────────┤
│ ☀|🌙  píldora de tema       │
│ 🔔 notificaciones  ⚙ prefs   │
│ PERFIL (avatar+n+rol+salir) │
└─────────────────────────────┘
```

Secciones → páginas (`hub/ui/shell.py:44-88`): `dashboard`, `catalog`, `search`,
`app`, `proposals`, `requests`, `knowledge`, `issues`, `reports`, `audit`,
`users` (+ internos `community`, `app_audit`, `failure_detail`, `notifications`).

### Ítem de navegación `_NavItem`

```
[accent 3×20px] [icono 20px] [gap 11px] [texto]  ── alto fijo 40 px
```

- Estados: **normal** / **hover** (fondo transición) / **activo** (barra acento +
  fondo `sidebar_active_bg`) / **foco teclado** visible.
- Animaciones: hover/acento **160 ms** `OutCubic` (interpola fondo con
  `QColor`), colapso de ancho **220 ms**.
- Accesibilidad: `focusPolicy=StrongFocus`, `accessibleName`, `tooltip`,
  navegación con Enter/flechas y colapso con tooltip flotante.

### Layout y márgenes

| Zona | Expandido (256) | Colapsado (72) |
|---|---|---|
| `brand row` | `(12,12,10,12)` | `(21,12,21,12)` |
| nav (scroll content) | `(12,6,12,16)` | `(4,6,4,16)` |
| contenedor perfil | `(12,10,12,10)` | `(15,6,15,6)` |
| logo card | visible | oculto (solo botón colapsar) |

En colapsado: el ícono del ítem queda **centrado** (left=right=24 en 72 px),
labels y leyendas ocultos, ítems a 40 px. Re-expandiendo restaura todo.

### Brand row y panel inferior

- Brand: `assets/logo_brand.png` dentro de una tarjeta blanca (`sidebar_card`)
  con borde `logo_card_border`; a su derecha el botón `panel-left` (colapsar).
- Panel inferior: píldora de tema **☀/🌙** (`_refresh_theme_button`), botones
  notificaciones/preferencias y tarjeta de perfil (avatar con inicial, nombre, rol,
  logout). Colores por `Theme.sidebar_*`.

## Mecánica del tema

1. `design.py` mantiene `_current_theme` y lo persiste (`save_theme`/`get_theme`).
2. `Shell._set_theme(mode)` → `apply_theme()` re-aplica QSS/paletas globales y
   llama `_refresh_sidebar_static()` para repintar el sidebar en el nuevo modo.
3. El botón píldora alterna y queda sincronizado con el modo activo.

## Trampas de Qt documentadas

- Un `QWidget` plano **no pinta `background-color`** por QSS: hace falta
  `setAttribute(WA_StyledBackground)`. Se aplica a `sidebar`, `sidebarNav` y
  `_NavItem`.
- Los selectores QSS globales (`QWidget { ... }`) **pierden por especificidad**
  contra estilos locales; por eso el sidebar usa selectores por objectName/id:
  `_NavItem#navItem`, `QLabel#navItemLabel`, `QLabel#sidebarSectionLabel`,
  `QLabel#brandLogo`, `QLabel#profileName`, `QLabel#profileRole`, `QLabel#prefsLabel`.
- Todo repintado de tema debe ejecutarse en el hilo de UI.