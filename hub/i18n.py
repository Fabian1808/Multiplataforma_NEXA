"""NEXA Productivity Hub — Módulo de Internacionalización (i18n).

Soporta: Español (es) e Inglés (en).
El idioma activo se persiste en %APPDATA%/NEXA/ProductivityHub/lang.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Traducciones COMPLETAS
# ---------------------------------------------------------------------------
_TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        # ── Navegación sidebar ──
        "nav.dashboard":    "Inicio",
        "nav.catalog":      "Catálogo",
        "nav.search":       "Búsqueda",
        "nav.app":          "Aplicaciones",
        "nav.proposals":    "Propuestas",
        "nav.requests":     "Solicitudes",
        "nav.issues":       "Incidencias",
        "nav.knowledge":    "Conocimiento",
        "nav.community":    "Comunidad",
        "nav.reports":      "Reportes",
        "nav.audit":        "Auditoría",
        "nav.users":        "Gestión de Usuarios",
        "nav.app_audit":    "Auditoría de Apps",
        "nav.failure":      "Detalle de Fallo",
        "nav.notifications":"Notificaciones",

        # ── Secciones del sidebar ──
        "section.main":     "PRINCIPAL",
        "section.manage":   "GESTIÓN",
        "section.knowledge":"CONOCIMIENTO",
        "section.analytics":"ANALÍTICA",
        "section.admin":    "ADMINISTRACIÓN",

        # ── Header ──
        "header.search_placeholder": "Buscar...",
        "header.theme_light":        "Cambiar a modo claro",
        "header.theme_dark":         "Cambiar a modo oscuro",

        # ── Auth / Login ──
        "login.subtitle":    "Productivity Hub",
        "login.user_label":  "Usuario",
        "login.user_placeholder": "Ingresa tu usuario",
        "login.pass_label":  "Contraseña",
        "login.pass_placeholder": "Ingresa tu contraseña",
        "login.btn":         "Iniciar Sesión",
        "login.footer":      "NEXA © 2026 · Productivity Hub",
        "login.empty_fields": "Ingresa usuario y contraseña.",
        "login.invalid":     "Credenciales incorrectas. Te quedan {n} intento(s).",
        "login.locked_temp": "Cuenta bloqueada temporalmente ({n}s).",
        "login.too_many":    "Demasiados intentos. Intenta de nuevo en {n}s.",

        # ── Perfil / Rol ──
        "role.admin":        "Administrador",
        "role.collaborator": "Colaborador",
        "action.preferences":"Preferencias",
        "action.logout":     "Cerrar sesión",
        "action.logout_confirm": "¿Está seguro que desea cerrar sesión?",
        "action.logout_title":   "Cerrar sesión",

        # ── Acceso ──
        "access.denied":    "⚠ No tiene permisos para acceder a esta sección.",
        "crumb.prefix":     "NEXA",
        "crumb.denied":     "Acceso denegado",

        # ── Splash ──
        "splash.starting":  "Iniciando...",
        "splash.db":        "Conectando base de datos...",
        "splash.services":  "Cargando servicios...",
        "splash.ui":        "Preparando interfaz...",
        "splash.ready":     "Listo",

        # ── Sidebar toggle ──
        "sidebar.collapse": "Contraer menú",
        "sidebar.expand":   "Expandir menú",

        # ── Dashboard KPIs ──
        "dashboard.welcome":          "Bienvenido",
        "dashboard.subtitle":         "Resumen de la plataforma NEXA Productivity Hub",
        "dashboard.favorites":        "Mis aplicaciones favoritas",
        "dashboard.pending_requests": "Solicitudes e Incidencias pendientes",
        "dashboard.recent_activity":  "Actualizaciones y Mejoras recientes",
        "dashboard.recent_tools":     "Aplicaciones recientemente utilizadas",
        "dashboard.no_data":          "Sin datos disponibles",
        "kpi.executions":             "Ejecuciones",
        "kpi.tools":                  "Herramientas",
        "kpi.users":                  "Usuarios",
        "kpi.projects":               "Proyectos",
        "kpi.requests":               "Solicitudes",
        "kpi.articles":               "Conocimiento",
        "kpi.posts":                  "Publicaciones",
        "kpi.incidents":              "Incidentes",
        "kpi.pending":                "Pendientes",
        "kpi.executions_count":       "{n} ejecuciones",

        # ── Salud de apps ──
        "health.active":    "{n} activas",
        "health.paused":    "{n} en pausa",
        "health.problems":  "{n} con problemas",
        "health.total":     "{n} en total",

        # ── Catálogo / Búsqueda ──
        "catalog.title":    "Catálogo de Aplicaciones",
        "catalog.search":   "Buscar aplicación...",
        "catalog.empty":    "No se encontraron aplicaciones.",
        "catalog.filter_all": "Todas",
        "search.placeholder": "Buscar en todo NEXA...",
        "search.results":   "Resultados para \"{q}\"",
        "search.no_results":"Sin resultados para \"{q}\"",

        # ── Propuestas ──
        "proposals.title":      "Nueva Propuesta de Automatización",
        "proposals.task":       "¿Qué tarea quieres automatizar?",
        "proposals.frequency":  "¿Con qué frecuencia?",
        "proposals.tools":      "Herramientas actuales",
        "proposals.steps":      "Pasos del proceso",
        "proposals.submit":     "Enviar Propuesta",
        "proposals.success":    "Propuesta enviada exitosamente.",

        # ── Solicitudes ──
        "requests.title":   "Solicitudes",
        "requests.empty":   "No hay solicitudes.",
        "requests.status_pending":  "Pendiente",
        "requests.status_active":   "Activo",
        "requests.status_resolved": "Resuelto",

        # ── Incidencias ──
        "issues.title":         "Reportar Incidencia",
        "issues.what_happened": "¿Qué ocurrió?",
        "issues.submit":        "Reportar",
        "issues.success":       "Incidencia reportada.",

        # ── Conocimiento ──
        "knowledge.title":  "Base de Conocimiento",
        "knowledge.search": "Buscar artículo...",
        "knowledge.empty":  "No hay artículos disponibles.",
        "knowledge.read":   "Leer más",

        # ── Reportes ──
        "reports.title":    "Centro de Reportes",
        "reports.export":   "Exportar",
        "reports.period":   "Período",
        "reports.empty":    "No hay reportes.",

        # ── Auditoría ──
        "audit.title":      "Registro de Auditoría",
        "audit.user":       "Usuario",
        "audit.action":     "Acción",
        "audit.date":       "Fecha",
        "audit.empty":      "Sin registros.",

        # ── Usuarios ──
        "users.title":      "Gestión de Usuarios",
        "users.add":        "Agregar Usuario",
        "users.name":       "Nombre",
        "users.email":      "Correo",
        "users.role":       "Rol",
        "users.status":     "Estado",
        "users.active":     "Activo",
        "users.inactive":   "Inactivo",

        # ── Comunidad ──
        "community.title":  "Comunidad NEXA",
        "community.post":   "Nueva Publicación",
        "community.empty":  "No hay publicaciones.",

        # ── Notificaciones ──
        "notifications.title": "Notificaciones",
        "notifications.empty": "No hay notificaciones.",
        "notifications.mark_read": "Marcar como leída",

        # ── Acciones comunes ──
        "action.save":      "Guardar",
        "action.cancel":    "Cancelar",
        "action.delete":    "Eliminar",
        "action.edit":      "Editar",
        "action.close":     "Cerrar",
        "action.back":      "Volver",
        "action.confirm":   "Confirmar",
        "action.search":    "Buscar",
        "action.filter":    "Filtrar",
        "action.export":    "Exportar",
        "action.refresh":   "Actualizar",

        # ── Estados ──
        "status.operational": "Operacional",
        "status.warning":     "Advertencia",
        "status.error":       "Error",
        "status.info":        "Información",
        "status.official":    "Oficial",
        "status.community":   "Comunidad",
        "status.beta":        "Beta",
        "status.deprecated":  "Obsoleto",

        # ── Mensajes de error ──
        "error.generic":    "Ha ocurrido un error. Inténtalo de nuevo.",
        "error.no_permission": "No tienes permisos para realizar esta acción.",
        "error.not_found":  "No se encontró el recurso solicitado.",
        "error.network":    "Error de conexión. Verifica tu red.",
    },
    "en": {
        # ── Navigation sidebar ──
        "nav.dashboard":    "Home",
        "nav.catalog":      "Catalog",
        "nav.search":       "Search",
        "nav.app":          "Applications",
        "nav.proposals":    "Proposals",
        "nav.requests":     "Requests",
        "nav.issues":       "Incidents",
        "nav.knowledge":    "Knowledge",
        "nav.community":    "Community",
        "nav.reports":      "Reports",
        "nav.audit":        "Audit",
        "nav.users":        "User Management",
        "nav.app_audit":    "App Audit",
        "nav.failure":      "Failure Detail",
        "nav.notifications":"Notifications",

        # ── Sidebar sections ──
        "section.main":     "MAIN",
        "section.manage":   "MANAGEMENT",
        "section.knowledge":"KNOWLEDGE",
        "section.analytics":"ANALYTICS",
        "section.admin":    "ADMINISTRATION",

        # ── Header ──
        "header.search_placeholder": "Search...",
        "header.theme_light":        "Switch to light mode",
        "header.theme_dark":         "Switch to dark mode",

        # ── Auth / Login ──
        "login.subtitle":    "Productivity Hub",
        "login.user_label":  "Username",
        "login.user_placeholder": "Enter your username",
        "login.pass_label":  "Password",
        "login.pass_placeholder": "Enter your password",
        "login.btn":         "Sign In",
        "login.footer":      "NEXA © 2026 · Productivity Hub",
        "login.empty_fields": "Enter your username and password.",
        "login.invalid":     "Invalid credentials. {n} attempt(s) remaining.",
        "login.locked_temp": "Account temporarily locked ({n}s).",
        "login.too_many":    "Too many attempts. Try again in {n}s.",

        # ── Profile / Role ──
        "role.admin":        "Administrator",
        "role.collaborator": "Collaborator",
        "action.preferences":"Preferences",
        "action.logout":     "Sign out",
        "action.logout_confirm": "Are you sure you want to sign out?",
        "action.logout_title":   "Sign out",

        # ── Access ──
        "access.denied":    "⚠ You don't have permission to access this section.",
        "crumb.prefix":     "NEXA",
        "crumb.denied":     "Access denied",

        # ── Splash ──
        "splash.starting":  "Starting...",
        "splash.db":        "Connecting database...",
        "splash.services":  "Loading services...",
        "splash.ui":        "Preparing interface...",
        "splash.ready":     "Ready",

        # ── Sidebar toggle ──
        "sidebar.collapse": "Collapse menu",
        "sidebar.expand":   "Expand menu",

        # ── Dashboard KPIs ──
        "dashboard.welcome":          "Welcome",
        "dashboard.subtitle":         "NEXA Productivity Hub summary",
        "dashboard.favorites":        "My favorite applications",
        "dashboard.pending_requests": "Pending Requests & Incidents",
        "dashboard.recent_activity":  "Recent Updates & Improvements",
        "dashboard.recent_tools":     "Recently used applications",
        "dashboard.no_data":          "No data available",
        "kpi.executions":             "Executions",
        "kpi.tools":                  "Tools",
        "kpi.users":                  "Users",
        "kpi.projects":               "Projects",
        "kpi.requests":               "Requests",
        "kpi.articles":               "Knowledge",
        "kpi.posts":                  "Posts",
        "kpi.incidents":              "Incidents",
        "kpi.pending":                "Pending",
        "kpi.executions_count":       "{n} executions",

        # ── App health ──
        "health.active":    "{n} active",
        "health.paused":    "{n} paused",
        "health.problems":  "{n} with issues",
        "health.total":     "{n} total",

        # ── Catalog / Search ──
        "catalog.title":    "Application Catalog",
        "catalog.search":   "Search application...",
        "catalog.empty":    "No applications found.",
        "catalog.filter_all": "All",
        "search.placeholder": "Search all of NEXA...",
        "search.results":   "Results for \"{q}\"",
        "search.no_results":"No results for \"{q}\"",

        # ── Proposals ──
        "proposals.title":      "New Automation Proposal",
        "proposals.task":       "What task do you want to automate?",
        "proposals.frequency":  "How often?",
        "proposals.tools":      "Current tools",
        "proposals.steps":      "Process steps",
        "proposals.submit":     "Submit Proposal",
        "proposals.success":    "Proposal successfully submitted.",

        # ── Requests ──
        "requests.title":   "Requests",
        "requests.empty":   "No requests found.",
        "requests.status_pending":  "Pending",
        "requests.status_active":   "Active",
        "requests.status_resolved": "Resolved",

        # ── Issues ──
        "issues.title":         "Report an Incident",
        "issues.what_happened": "What happened?",
        "issues.submit":        "Submit",
        "issues.success":       "Incident reported.",

        # ── Knowledge ──
        "knowledge.title":  "Knowledge Base",
        "knowledge.search": "Search article...",
        "knowledge.empty":  "No articles available.",
        "knowledge.read":   "Read more",

        # ── Reports ──
        "reports.title":    "Reports Center",
        "reports.export":   "Export",
        "reports.period":   "Period",
        "reports.empty":    "No reports.",

        # ── Audit ──
        "audit.title":      "Audit Log",
        "audit.user":       "User",
        "audit.action":     "Action",
        "audit.date":       "Date",
        "audit.empty":      "No records.",

        # ── Users ──
        "users.title":      "User Management",
        "users.add":        "Add User",
        "users.name":       "Name",
        "users.email":      "Email",
        "users.role":       "Role",
        "users.status":     "Status",
        "users.active":     "Active",
        "users.inactive":   "Inactive",

        # ── Community ──
        "community.title":  "NEXA Community",
        "community.post":   "New Post",
        "community.empty":  "No posts yet.",

        # ── Notifications ──
        "notifications.title": "Notifications",
        "notifications.empty": "No notifications.",
        "notifications.mark_read": "Mark as read",

        # ── Common actions ──
        "action.save":      "Save",
        "action.cancel":    "Cancel",
        "action.delete":    "Delete",
        "action.edit":      "Edit",
        "action.close":     "Close",
        "action.back":      "Back",
        "action.confirm":   "Confirm",
        "action.search":    "Search",
        "action.filter":    "Filter",
        "action.export":    "Export",
        "action.refresh":   "Refresh",

        # ── Statuses ──
        "status.operational": "Operational",
        "status.warning":     "Warning",
        "status.error":       "Error",
        "status.info":        "Info",
        "status.official":    "Official",
        "status.community":   "Community",
        "status.beta":        "Beta",
        "status.deprecated":  "Deprecated",

        # ── Error messages ──
        "error.generic":    "An error occurred. Please try again.",
        "error.no_permission": "You don't have permission to perform this action.",
        "error.not_found":  "The requested resource was not found.",
        "error.network":    "Connection error. Check your network.",
    },
}

# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------
_APPDATA   = os.environ.get("APPDATA", str(Path.home()))
_LANG_PATH = Path(_APPDATA) / "NEXA" / "ProductivityHub" / "lang.json"

_DEFAULT_LANG = "es"
_SUPPORTED    = frozenset(("es", "en"))


def _load_lang() -> str:
    try:
        if _LANG_PATH.exists():
            with open(_LANG_PATH, encoding="utf-8") as f:
                data = json.load(f)
            lang = data.get("lang", _DEFAULT_LANG)
            return lang if lang in _SUPPORTED else _DEFAULT_LANG
    except Exception:
        pass
    return _DEFAULT_LANG


def save_lang(lang: str) -> None:
    """Persiste la preferencia de idioma."""
    _LANG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_LANG_PATH, "w", encoding="utf-8") as f:
        json.dump({"lang": lang}, f)


_current_lang: str = _load_lang()

# Callbacks registrados para notificar cambios de idioma.
_lang_change_callbacks: list = []


def get_lang() -> str:
    return _current_lang


def set_lang(lang: str) -> None:
    global _current_lang
    if lang not in _SUPPORTED:
        return
    _current_lang = lang
    save_lang(lang)
    for cb in list(_lang_change_callbacks):
        try:
            cb(lang)
        except Exception:
            pass


def on_lang_change(callback) -> None:
    """Registra un callback que se llama cuando cambia el idioma."""
    if callback not in _lang_change_callbacks:
        _lang_change_callbacks.append(callback)


def off_lang_change(callback) -> None:
    """Elimina un callback registrado."""
    try:
        _lang_change_callbacks.remove(callback)
    except ValueError:
        pass


def tr(key: str, fallback: str = "") -> str:
    """Devuelve la traducción de `key` en el idioma activo.

    Si la clave no existe, devuelve `fallback` o la propia clave.
    """
    lang_dict = _TRANSLATIONS.get(_current_lang, {})
    if key in lang_dict:
        return lang_dict[key]
    # Fallback al español
    lang_dict_es = _TRANSLATIONS.get("es", {})
    if key in lang_dict_es:
        return lang_dict_es[key]
    return fallback or key
