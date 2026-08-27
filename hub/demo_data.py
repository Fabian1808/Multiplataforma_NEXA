"""Demo — Generador de datos ficticios para showcase de la plataforma NEXA."""

from __future__ import annotations

import logging
import random
import secrets
from datetime import datetime, timedelta
from typing import Any

from hub.infrastructure.database import Database
from hub.core.auth_service import AuthService
from hub.core.audit_service import AuditService
from hub.core.metrics_collector import MetricsCollector
from hub.core.notification_service import NotificationService
from hub.core.request_service import RequestService
from hub.core.knowledge_service import KnowledgeService
from hub.core.feed_service import FeedService
from hub.core.project_service import ProjectService

logger = logging.getLogger(__name__)

_AREAS = ["Contratos", "TI", "Recursos Humanos", "Finanzas", "Operaciones", "Comercial", "Legal", "Logística"]
_DEPT_NAMES = ["Tecnología", "Administración", "Recursos Humanos", "Finanzas", "Operaciones", "Comercial"]
_DEPT_CODES = ["TI", "ADM", "RRHH", "FIN", "OPS", "COM"]
_NAMES = [
    "Carlos Mendoza", "Ana García", "Roberto Díaz", "María López", "Pedro Sánchez",
    "Laura Martínez", "Diego Torres", "Sofia Ramírez", "Andrés Vargas", "Valentina Cruz",
    "Fernando Reyes", "Camila Ortiz", "Miguel Herrera", "Isabella Flores", "Javier Morales",
    "Luciana Peña", "Ricardo Delgado", "Daniela Campos", "Alejandro Silva", "Gabriela Rojas",
    "Oscar Medina", "Patricia Nuñez", "Hugo Castillo", "Carolina Vega", "Sergio Ríos",
    "Natalia Romero", "Eduardo Luna", "Mónica Estrada", "Pablo Aguilar", "Claudia Mora",
]
_PLUGIN_IDS = ["horas_extras", "sap_automation", "sap_module", "excel_macros", "email_automation",
               "report_generator", "data_validator", "backup_tool", "scheduler", "document_parser"]
_PLUGIN_NAMES = [
    "Horas Extras", "Automatización SAP", "Módulo SAP", "Macros Excel", "Automatización Email",
    "Generador de Reportes", "Validador de Datos", "Herramienta Backup", "Planificador", "Parser de Documentos",
]
_POST_TYPES = ["general", "logro", "noticia", "tutorial", "pregunta"]
_PRIORITIES = ["baja", "media", "alta", "critica"]
_REQUEST_TYPES = ["ayuda", "idea", "incidente"]
_STATUSES = ["enviada", "en_revision", "aprobada", "en_desarrollo", "pruebas", "publicada"]
_KNOWLEDGE_CATS = ["SAP", "Procesos", "Herramientas", "Onboarding", "Troubleshooting", "Mejores Prácticas"]
_NOTIFICATION_TYPES = [
    "request_created", "request_assigned", "request_status_changed",
    "comment_added", "mention", "like_received", "task_assigned",
    "project_updated", "welcome", "system_update",
]
POST_CONTENTS = [
    ("Logro del equipo", "Hoy completamos la automatización del reporte mensual de contratos. Redujimos el tiempo de procesamiento de 4 horas a 15 minutos. #automatización #efficiency", "logro"),
    ("Nuevo tutorial disponible", "Publicamos un tutorial paso a paso para usar el módulo de Horas Extras. Encuéntralo en la Base de Conocimiento.", "tutorial"),
    ("Pregunta sobre SAP", "¿Alguien ha experimentado un error al ejecutar el reporte de inventario en SAP? Me aparece un timeout después de 5 minutos.", "pregunta"),
    ("Noticia de la empresa", "NEXA ha sido reconocida como Top Employer 2026. Esto se logra gracias al esfuerzo de todo el equipo.", "noticia"),
    ("Mejores prácticas", "Comparto algunas mejores prácticas para usar las macros de Excel de forma segura: 1) Siempre hacer backup, 2) Revisar las macros antes de ejecutar, 3) Usar la versión de plantilla oficial.", "tutorial"),
    ("Solicitud de capacitación", "Me gustaría solicitar una capacitación sobre las nuevas funcionalidades de SAP S/4HANA. ¿Quién más estaría interesado?", "general"),
    ("Actualización del sistema", "El Hub se ha actualizado a la versión 2.0 con mejoras significativas en rendimiento y nuevas funcionalidades.", "noticia"),
    ("Tutorial: Automatización de emails", "Aprende a configurar la automatización de envío de reportes por email. Paso a paso con imágenes.", "tutorial"),
    ("Incidente resuelto", "Se resolvió el problema de conexión con el servidor de SAP. Ya puede usar todas las herramientas normalmente.", "general"),
    ("¡Bienvenida a los nuevos!", "Damos la bienvenida a 5 nuevos miembros del equipo de TI. Están en periodo de inducción esta semana.", "general"),
]

KNOWLEDGE_ARTICLES = [
    ("Guía de Horas Extras", "## Guía completa para el sistema de horas extras\n\n### 1. Acceso\nIngrese al módulo desde el menú principal.\n\n### 2. Registro\nComplete el formulario con los datos solicitados.\n\n### 3. Aprobación\nSu supervisor recibirá una notificación para aprobar la solicitud.", "SAP", "horas_extras"),
    ("Configuración de SAP", "## Configuración inicial de SAP\n\n### Parámetros de conexión\n- Servidor: sap.nexa.local\n- Puerto: 3300\n- Sistema: PRD\n\n### Credenciales\nUsar credenciales de Active Directory.", "SAP", "sap_automation"),
    ("Errores comunes en SAP", "## Errores frecuentes y soluciones\n\n### Error: Connection timeout\n**Causa:** Servidor sobrecargado\n**Solución:** Esperar 5 minutos y reintentar\n\n### Error: Authorization failed\n**Causa:** Permisos insuficientes\n**Solución:** Solicitar permisos al administrador", "Troubleshooting", "sap_automation"),
    ("Plantilla de reportes Excel", "## Plantilla oficial de reportes\n\n### Estructura\n- Hoja 1: Datos brutos\n- Hoja 2: Resumen ejecutivo\n- Hoja 3: Gráficos\n\n### Instrucciones\n1. Descargar plantilla\n2. Completar datos en Hoja 1\n3. Los demás se actualizan automáticamente", "Herramientas", "excel_macros"),
    ("Onboarding de nuevos usuarios", "## Bienvenido a NEXA\n\n### Primeros pasos\n1. Completar registro en Active Directory\n2. Solicitar acceso al Hub\n3. Explorar el catálogo de herramientas\n4. Revisar la base de conocimiento\n\n### Contactos\n- IT Helpdesk: helpdesk@nexa.com", "Onboarding", None),
]


def seed_demo_data(db: Database) -> None:
    """Genera datos ficticios completos para demo de la plataforma."""
    auth = AuthService(db)
    audit = AuditService(db)
    metrics = MetricsCollector(db)
    notifications = NotificationService(db)
    requests_svc = RequestService(db)
    knowledge_svc = KnowledgeService(db)
    feed_svc = FeedService(db)
    projects_svc = ProjectService(db)

    now = datetime.now()
    logger.info("Iniciando generación de datos demo...")

    existing_users = db.fetchall("SELECT id FROM users WHERE username != 'fabian'")
    if len(existing_users) >= 20:
        logger.info("Datos demo ya existen, saltando...")
        return

    departments: list[str] = []
    for i, (name, code) in enumerate(zip(_DEPT_NAMES, _DEPT_CODES)):
        dept_id = f"dept_{secrets.token_hex(8)}"
        db.execute(
            "INSERT OR IGNORE INTO departments (id, name, code, is_active, created_at, updated_at, created_by) VALUES (?, ?, ?, 1, ?, ?, 'system')",
            (dept_id, name, code, now.isoformat(), now.isoformat()),
        )
        departments.append(dept_id)
    db.commit()

    users: list[dict[str, Any]] = []
    for i, name in enumerate(_NAMES):
        username = name.lower().replace(" ", ".").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        area = _AREAS[i % len(_AREAS)]
        dept = departments[i % len(departments)]
        role = "administrador" if i < 3 else "gestor" if i < 8 else "usuario"
        user = auth.create_user(username, name, f"{username}@nexa.com", "", area=area, department_id=dept, role=role, created_by="system")
        users.append(user)
        if i < 15:
            days_ago = random.randint(1, 30)
            login_time = (now - timedelta(days=days_ago, hours=random.randint(0, 12))).isoformat()
            db.execute("UPDATE users SET last_login = ? WHERE id = ?", (login_time, user["id"]))
    db.commit()
    logger.info("Creados %d usuarios demo", len(users))

    for user in users:
        for _ in range(random.randint(2, 15)):
            days_ago = random.randint(0, 60)
            action = random.choice(["create", "update", "view", "search", "execute", "login"])
            module = random.choice(["requests", "knowledge", "plugins", "projects", "feed", "system"])
            entity_type = random.choice(["request", "article", "plugin", "project", "post"])
            entity_id = str(random.randint(1, 100))
            entity_name = random.choice(["Solicitud", "Artículo", "Plugin", "Proyecto", "Publicación"])
            ts = (now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))).isoformat()
            db.execute(
                "INSERT INTO audit_log (user_id, action, module, entity_type, entity_id, entity_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user["id"], action, module, entity_type, entity_id, entity_name, ts),
            )
    db.commit()
    logger.info("Audit log generado")

    for article_title, content, category, plugin_id in KNOWLEDGE_ARTICLES:
        author = random.choice(users[:10])
        days_ago = random.randint(1, 90)
        ts = (now - timedelta(days=days_ago)).isoformat()
        db.execute(
            """INSERT INTO knowledge_articles (title, content, summary, category, tags, status, version, author, plugin_id, view_count, helpful_count, created_at, updated_at, created_by)
               VALUES (?, ?, ?, ?, ?, 'publicado', 1, ?, ?, ?, ?, ?, ?, ?)""",
            (article_title, content, content[:100], category, category.lower(), author["name"], plugin_id or "",
             random.randint(10, 500), random.randint(1, 50), ts, ts, author["id"]),
        )
    db.commit()
    logger.info("Artículos de conocimiento creados")

    for i in range(30):
        user = random.choice(users)
        req_type = random.choice(_REQUEST_TYPES)
        priority = random.choice(_PRIORITIES)
        status = random.choice(_STATUSES)
        days_ago = random.randint(0, 60)
        ts = (now - timedelta(days=days_ago)).isoformat()
        desc = f"Solicitud de {req_type} sobre {_PLUGIN_NAMES[i % len(_PLUGIN_NAMES)]}. {random.choice(['Urgente', 'Importante', 'Regular', 'Cuando sea posible'])}."
        db.execute(
            """INSERT INTO requests (user_id, request_type, title, description, area, priority, status, workflow_state, created_at, updated_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user["id"], req_type, f"Solicitud #{i+1}", desc, user.get("area", ""), priority, status,
             "completada" if status in ("publicada", "cerrada") else "en_proceso" if status == "en_desarrollo" else "nueva",
             ts, ts, user["id"]),
        )
    db.commit()
    logger.info("Solicitudes demo creadas")

    for i, (title, content, ptype) in enumerate(POST_CONTENTS):
        user = users[i % len(users)]
        days_ago = random.randint(0, 30)
        ts = (now - timedelta(days=days_ago)).isoformat()
        db.execute(
            """INSERT INTO posts (user_id, title, content, visibility, post_type, tags, likes_count, comments_count, created_at, updated_at, created_by)
               VALUES (?, ?, ?, 'publico', ?, ?, ?, ?, ?, ?, ?)""",
            (user["id"], title, content, ptype, ptype, random.randint(0, 25), random.randint(0, 10), ts, ts, user["id"]),
        )
    db.commit()
    logger.info("Publicaciones de comunidad creadas")

    project_names = [
        ("Automatización de Reportes Mensuales", "Automatizar la generación de reportes mensuales de contratos y finanzas."),
        ("Migración SAP S/4HANA", "Migrar el sistema SAP actual a la versión S/4HANA."),
        ("Portal de Autoservicio", "Crear un portal donde los usuarios puedan realizar consultas y trámites sin intervención de TI."),
        ("Integración Outlook-Hub", "Integrar el sistema de notificaciones con Microsoft Outlook."),
        ("Dashboard de KPIs en Tiempo Real", "Desarrollar un dashboard ejecutivo con métricas en tiempo real."),
        ("Automatización de Nómina", "Automatizar el cálculo y envío de nómina mensual."),
    ]
    for pname, pdesc in project_names:
        owner = random.choice(users[:5])
        status = random.choice(["planeacion", "en_progreso", "completado"])
        proj_id = projects_svc.create_project(
            name=pname, description=pdesc, status=status,
            priority=random.choice(_PRIORITIES), owner_id=owner["id"],
            department_id=random.choice(departments),
            created_by=owner["id"],
        )
        for j in range(random.randint(3, 8)):
            assignee = random.choice(users)
            task_status = random.choice(["pendiente", "en_progreso", "completada"])
            projects_svc.create_task(
                project_id=proj_id, title=f"Tarea {j+1}: {pname[:20]}...",
                description=f"Subtarea del proyecto {pname}",
                status=task_status, priority=random.choice(_PRIORITIES),
                assignee_id=assignee["id"], created_by=owner["id"],
            )
    db.commit()
    logger.info("Proyectos y tareas demo creados")

    for user in users[:20]:
        for _ in range(random.randint(1, 8)):
            days_ago = random.randint(0, 30)
            ts = (now - timedelta(days=days_ago, hours=random.randint(0, 23))).isoformat()
            ntype = random.choice(_NOTIFICATION_TYPES)
            title = f"Notificación: {ntype.replace('_', ' ').title()}"
            db.execute(
                """INSERT INTO notifications (user_id, notification_type, title, message, priority, read, created_at, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user["id"], ntype, title, f"Detalle de la notificación para {user['name']}",
                 random.choice(["normal", "alta"]), random.choice([0, 0, 1]), ts, "system"),
            )
    db.commit()
    logger.info("Notificaciones demo creadas")

    for i in range(50):
        plugin_idx = random.randint(0, len(_PLUGIN_IDS) - 1)
        days_ago = random.randint(0, 60)
        ts = (now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))).isoformat()
        success = random.random() > 0.15
        duration = round(random.uniform(0.5, 30.0), 2)
        status = "exito" if success else "error"
        db.execute(
            """INSERT INTO executions (plugin_id, user_id, status, started_at, finished_at, duration_seconds, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (_PLUGIN_IDS[plugin_idx], random.choice(users)["id"], status, ts, ts, duration, ts, ts),
        )
        today = ts[:10]
        db.execute(
            """INSERT INTO metrics_daily (date, metric_name, metric_value, dimension, created_at)
               VALUES (?, 'executions', 1, ?, ?)
               ON CONFLICT(date, metric_name, dimension) DO UPDATE SET metric_value = metric_value + 1""",
            (today, _PLUGIN_IDS[plugin_idx], ts),
        )
    db.commit()
    logger.info("Ejecuciones y métricas demo generadas")

    for i in range(20):
        user = random.choice(users)
        days_ago = random.randint(0, 30)
        ts = (now - timedelta(days=days_ago)).isoformat()
        db.execute(
            "INSERT INTO searches (query, results_count, user_id, searched_at) VALUES (?, ?, ?, ?)",
            (f"buscar {_PLUGIN_NAMES[i % len(_PLUGIN_NAMES)].lower()}", random.randint(0, 5), user["id"], ts),
        )
    db.commit()
    logger.info("Búsquedas demo generadas")

    for _ in range(8):
        user = random.choice(users)
        db.execute(
            "INSERT INTO incidents (title, description, severity, status, reporter_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"Incidente en {_PLUGIN_NAMES[random.randint(0, len(_PLUGIN_NAMES)-1)]}",
             "Descripción del incidente reportado por el usuario.",
             random.choice(["baja", "media", "alta"]),
             random.choice(["abierto", "en_progreso", "resuelto"]),
             user["id"], now.isoformat(), now.isoformat()),
        )
    db.commit()
    logger.info("Incidentes demo creados")

    integrations = [
        ("SAP ECC", "sap", "activo", "Integración con SAP ECC para módulos FI/CO"),
        ("Microsoft Outlook", "email", "activo", "Conector de correo electrónico"),
        ("Active Directory", "ldap", "activo", "Autenticación corporativa"),
        ("SharePoint", "storage", "configurando", "Almacenamiento de documentos"),
    ]
    for iname, itype, istatus, idesc in integrations:
        int_id = f"int_{secrets.token_hex(8)}"
        db.execute(
            """INSERT INTO integrations (id, name, integration_type, status, description, created_at, updated_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (int_id, iname, itype, istatus, idesc, now.isoformat(), now.isoformat(), "system"),
        )
    db.commit()
    logger.info("Integraciones demo creadas")

    logger.info("=== Datos demo generados exitosamente ===")
