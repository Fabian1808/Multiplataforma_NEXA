"""UI — User Management. Gestión completa de usuarios: crear, editar, activar/desactivar, eliminar, restablecer credenciales."""

from __future__ import annotations

import logging

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from hub.core.auth_service import AuthService
from hub.core.audit_service import AuditService
from hub.ui.common.design import (
    Theme,
    NEXAStyles,
    ACCENT,
    ERROR,
    INFO,
    Icon,
    SUCCESS,
    WARNING,
    get_font
)

logger = logging.getLogger(__name__)

_ROLE_COLORS = {"administrador": ACCENT, "gestor": WARNING, "desarrollador": INFO, "usuario": SUCCESS}
_STATUS_COLORS = {1: SUCCESS, 0: ERROR}


def _role_label(role: str) -> str:
    return {"administrador": "Administrador", "gestor": "Gestor", "desarrollador": "Desarrollador", "usuario": "Usuario"}.get(role, role.capitalize())


class UserFormDialog(QDialog):
    """Modal para crear o editar un usuario."""

    def __init__(self, auth: AuthService, roles: list[str],
                 user: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._auth = auth
        self._user = user
        self._is_edit = user is not None
        self.setWindowTitle("Editar usuario" if self._is_edit else "Agregar usuario")
        self.setModal(True)
        self.setMinimumWidth(440)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Editar usuario" if self._is_edit else "Nuevo usuario")
        title.setFont(get_font(16, weight=700))
        title.setStyleSheet(f"color: {Theme.text()};")
        root.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name = QLineEdit()
        self._name.setStyleSheet(NEXAStyles.input())
        self._name.setPlaceholderText("Nombre completo")
        form.addRow("Nombre:", self._name)

        self._username = QLineEdit()
        self._username.setStyleSheet(NEXAStyles.input())
        self._username.setPlaceholderText("usuario_acceso")
        form.addRow("Usuario:", self._username)

        self._email = QLineEdit()
        self._email.setStyleSheet(NEXAStyles.input())
        self._email.setPlaceholderText("correo@nexa.com")
        form.addRow("Correo:", self._email)

        self._role = QComboBox()
        self._role.setStyleSheet(NEXAStyles.combo_box())
        for r in roles:
            self._role.addItem(_role_label(r), r)
        form.addRow("Rol:", self._role)

        self._area = QLineEdit()
        self._area.setStyleSheet(NEXAStyles.input())
        self._area.setPlaceholderText("Área / Departamento")
        form.addRow("Área:", self._area)

        self._password = QLineEdit()
        self._password.setStyleSheet(NEXAStyles.input())
        self._password.setPlaceholderText("Contraseña inicial" if not self._is_edit else "Dejar vacío para no cambiar")
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Contraseña:", self._password)

        self._password_confirm = QLineEdit()
        self._password_confirm.setStyleSheet(NEXAStyles.input())
        self._password_confirm.setPlaceholderText("Repetir contraseña")
        self._password_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        if self._is_edit:
            self._password_confirm.setVisible(False)
        form.addRow("Confirmar:", self._password_confirm)

        root.addLayout(form)

        if self._is_edit:
            self._name.setText(user.get("name", ""))
            self._username.setText(user.get("username", ""))
            self._email.setText(user.get("email", ""))
            self._area.setText(user.get("area", ""))
            idx = self._role.findData(user.get("roles", ["usuario"])[0] if user.get("roles") else "usuario")
            if idx >= 0:
                self._role.setCurrentIndex(idx)

        btns = QDialogButtonBox()
        save = btns.addButton("Guardar", QDialogButtonBox.ButtonRole.AcceptRole)
        save.setStyleSheet(NEXAStyles.primary_button())
        cancel = btns.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        cancel.setStyleSheet(NEXAStyles.secondary_button())
        btns.accepted.connect(self._validate_and_accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _validate_and_accept(self) -> None:
        name = self._name.text().strip()
        username = self._username.text().strip()
        email = self._email.text().strip()
        role = self._role.currentData()
        password = self._password.text()
        confirm = self._password_confirm.text()

        if not name or not username:
            QMessageBox.warning(self, "Datos incompletos", "El nombre y el usuario son obligatorios.")
            return
        if "@" not in email:
            QMessageBox.warning(self, "Correo inválido", "Ingrese un correo electrónico válido.")
            return

        existed_user_id = self._user["id"] if self._user else ""
        if self._auth.username_exists(username, exclude_user_id=existed_user_id):
            QMessageBox.warning(self, "Usuario duplicado", f"El usuario '{username}' ya está en uso.")
            return

        if not self._is_edit:
            if not password:
                QMessageBox.warning(self, "Contraseña requerida", "Debe asignar una contraseña inicial.")
                return
            if password != confirm:
                QMessageBox.warning(self, "Contraseñas no coinciden", "Las contraseñas no coinciden.")
                return
            if len(password) < 4:
                QMessageBox.warning(self, "Contraseña débil", "La contraseña debe tener al menos 4 caracteres.")
                return

        values = {
            "name": name,
            "username": username,
            "email": email,
            "role": role,
            "area": self._area.text().strip(),
        }
        if password:
            values["password"] = password
        self._result = values
        self.accept()

    def get_data(self) -> dict[str, Any]:
        return getattr(self, "_result", {})


class UserManagementView(QWidget):
    """Gestión de usuarios del sistema (RBAC protegido)."""

    data_changed = Signal()

    def __init__(self, auth: AuthService | None = None, audit: AuditService | None = None,
                 current_user_id: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._auth = auth
        self._audit = audit
        self._current_user_id = current_user_id
        self._users: list[dict[str, Any]] = []
        self._roles: list[str] = ["administrador", "gestor", "desarrollador", "usuario"]
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ---- Header ----
        header_row = QHBoxLayout()
        header_icon = Icon("users", 18)
        header_icon.set_color(ACCENT)
        header_row.addWidget(header_icon)
        header = QLabel("Gestión de Usuarios")
        header.setFont(get_font(18, weight=700))
        header.setStyleSheet(f"color: {Theme.text()};")
        header_row.addWidget(header, stretch=1)

        self._add_btn = QPushButton("  + Agregar usuario")
        self._add_btn.setStyleSheet(NEXAStyles.primary_button())
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._on_add_user)
        header_row.addWidget(self._add_btn)
        layout.addLayout(header_row)

        # Explicación de Roles
        roles_desc = QLabel(
            "<b>Permisos de Roles:</b><br>"
            "<b>• Administrador:</b> Control total de la plataforma.<br>"
            "<b>• Gestor:</b> Gestiona aplicaciones, aprobaciones de mejoras e incidencias.<br>"
            "<b>• Desarrollador:</b> Mantiene el código de las aplicaciones y actualiza la documentación.<br>"
            "<b>• Usuario:</b> Puede utilizar aplicaciones y generar solicitudes de mejora/incidencias."
        )
        roles_desc.setFont(get_font(11))
        roles_desc.setStyleSheet(f"color: {Theme.text_secondary()}; background-color: {Theme.input_bg()}; padding: 12px; border: 1px solid {Theme.border()}; border-radius: 8px;")
        layout.addWidget(roles_desc)

        # ---- Toolbar (búsqueda + filtros) ----
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Buscar por nombre, usuario o correo...")
        self._search.setStyleSheet(NEXAStyles.search_input())
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self._search, stretch=1)

        self._role_filter = QComboBox()
        self._role_filter.setStyleSheet(NEXAStyles.combo_box())
        self._role_filter.addItem("Todos los roles", "")
        for r in self._roles:
            self._role_filter.addItem(_role_label(r), r)
        self._role_filter.currentIndexChanged.connect(self._apply_filters)
        toolbar.addWidget(self._role_filter)

        self._status_filter = QComboBox()
        self._status_filter.setStyleSheet(NEXAStyles.combo_box())
        self._status_filter.addItem("Todos los estados", "")
        self._status_filter.addItem("Activos", "1")
        self._status_filter.addItem("Inactivos", "0")
        self._status_filter.currentIndexChanged.connect(self._apply_filters)
        toolbar.addWidget(self._status_filter)
        layout.addLayout(toolbar)

        # ---- Stats ----
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        self._total_label = QLabel("Total: 0")
        self._total_label.setFont(get_font(12, weight=700))
        self._total_label.setStyleSheet(f"color: {Theme.text()};")
        stats_row.addWidget(self._total_label)
        self._admin_label = QLabel("Administradores: 0")
        self._admin_label.setFont(get_font(11))
        self._admin_label.setStyleSheet(f"color: {ACCENT};")
        stats_row.addWidget(self._admin_label)
        self._gestor_label = QLabel("Gestores: 0")
        self._gestor_label.setFont(get_font(11))
        self._gestor_label.setStyleSheet(f"color: {WARNING};")
        stats_row.addWidget(self._gestor_label)
        self._active_label = QLabel("Activos: 0")
        self._active_label.setFont(get_font(11))
        self._active_label.setStyleSheet(f"color: {SUCCESS};")
        stats_row.addWidget(self._active_label)
        stats_row.addStretch()
        layout.addLayout(stats_row)

        # ---- Users grid ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(NEXAStyles.scroll_area())
        content = QWidget()
        content.setStyleSheet(f"background: {Theme.bg()};")
        self._grid = QGridLayout(content)
        self._grid.setSpacing(12)
        self._grid.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        self._empty_label = QLabel("No hay usuarios registrados")
        self._empty_label.setFont(get_font(14))
        self._empty_label.setStyleSheet(f"color: {Theme.text_muted()}; padding: 40px;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_roles(self, roles: list[str]) -> None:
        self._roles = roles or self._roles
        self._role_filter.blockSignals(True)
        self._role_filter.clear()
        self._role_filter.addItem("Todos los roles", "")
        for r in self._roles:
            self._role_filter.addItem(_role_label(r), r)
        self._role_filter.blockSignals(False)
        self._apply_filters()

    def refresh_style(self) -> None:
        """Re-aplica el tema actual (claro/oscuro) re-renderizando."""
        content = self._grid.parentWidget()
        if content is not None:
            content.setStyleSheet(f"background: {Theme.bg()};")
        self._apply_filters()

    def set_users(self, users: list[dict]) -> None:
        self._users = users or []
        self._apply_filters()

    # ------------------------------------------------------------------
    # Filters & render
    # ------------------------------------------------------------------
    def _apply_filters(self) -> None:
        q = self._search.text().strip().lower()
        role = self._role_filter.currentData()
        status = self._status_filter.currentData()
        self._update_stats(self._users)
        self._render(self._filtered(self._users, q, role, status))

    @staticmethod
    def _filtered(users: list[dict], q: str, role: str, status: str) -> list[dict]:
        out = []
        for u in users:
            if role and role not in u.get("roles", []):
                continue
            if status == "1" and not u.get("is_active"):
                continue
            if status == "0" and u.get("is_active"):
                continue
            if q:
                hay = " ".join([
                    str(u.get("name", "")), str(u.get("username", "")),
                    str(u.get("email", "")), str(u.get("area", "")),
                ]).lower()
                if q not in hay:
                    continue
            out.append(u)
        return out

    def _update_stats(self, users: list[dict]) -> None:
        total = len(users)
        admins = sum(1 for u in users if "administrador" in u.get("roles", []))
        gestores = sum(1 for u in users if "gestor" in u.get("roles", []))
        activos = sum(1 for u in users if u.get("is_active"))
        self._total_label.setText(f"Total: {total}")
        self._admin_label.setText(f"Administradores: {admins}")
        self._gestor_label.setText(f"Gestores: {gestores}")
        self._active_label.setText(f"Activos: {activos}")

    def _render(self, users: list[dict]) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not users:
            if self._empty_label.parentWidget() is None:
                self._grid.addWidget(self._empty_label, 0, 0, 1, 2)
            else:
                self._grid.addWidget(self._empty_label, 0, 0, 1, 2)
            return

        for i, user in enumerate(users):
            card = self._build_user_card(user)
            self._grid.addWidget(card, i // 2, i % 2)

    def _build_user_card(self, user: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(NEXAStyles.card_no_hover())
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        # Top: avatar + info + status
        top = QHBoxLayout()
        top.setSpacing(12)

        is_active = bool(user.get("is_active"))
        avatar_frame = QFrame()
        avatar_frame.setFixedSize(44, 44)
        avatar_frame.setStyleSheet(
            f"background-color: {ACCENT + '20' if is_active else Theme.hover_bg()};"
            f"border-radius: 22px; border: none;")
        av_lay = QHBoxLayout(avatar_frame)
        av_lay.setContentsMargins(0, 0, 0, 0)
        avatar = Icon("user", 20)
        avatar.set_color(ACCENT if is_active else Theme.text_muted())
        av_lay.addWidget(avatar)
        top.addWidget(avatar_frame)

        info = QVBoxLayout()
        info.setSpacing(1)
        name_lbl = QLabel(user.get("name", user.get("username", "")))
        name_lbl.setFont(get_font(13, weight=700))
        name_lbl.setStyleSheet(f"color: {Theme.text() if is_active else Theme.text_muted()};")
        name_lbl.setWordWrap(True)
        info.addWidget(name_lbl)

        roles = user.get("roles", [])
        role_text = ", ".join(_role_label(r) for r in roles) if roles else "Sin rol"
        role_lbl = QLabel(f"@{user.get('username', '')}  ·  {role_text}")
        role_lbl.setFont(get_font(10))
        role_lbl.setStyleSheet(f"color: {Theme.text_secondary()};")
        info.addWidget(role_lbl)

        meta = user.get("email", "")
        if user.get("area"):
            meta = f"{user.get('area')} · {meta}" if meta else user.get("area")
        meta_lbl = QLabel(meta or "—")
        meta_lbl.setFont(get_font(10))
        meta_lbl.setStyleSheet(f"color: {Theme.text_muted()};")
        meta_lbl.setWordWrap(True)
        info.addWidget(meta_lbl)
        top.addLayout(info, stretch=1)

        status_lbl = QLabel("Activo" if is_active else "Inactivo")
        status_color = _STATUS_COLORS.get(int(is_active), Theme.text_muted())
        status_lbl.setStyleSheet(NEXAStyles.badge("Activo" if is_active else "Inactivo", status_color))
        top.addWidget(status_lbl, 0, Qt.AlignmentFlag.AlignTop)
        card_layout.addLayout(top)

        # Self label
        is_self = (user.get("id") == self._current_user_id)

        # Actions
        actions = QHBoxLayout()
        actions.setSpacing(6)

        def _mk_action(text: str, icon: str, color: str, handler) -> QPushButton:
            btn = QPushButton(f"  {text}")
            btn.setStyleSheet(NEXAStyles.ghost_button())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {color}; border: 1px solid {color}40; "
                f"border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: 600; }}"
                f"QPushButton:hover {{ background: {color}14; }}")
            btn.clicked.connect(lambda _=False, h=handler: h())
            return btn

        edit_btn = _mk_action("Editar", "user", ACCENT, lambda: self._on_edit_user(user))
        actions.addWidget(edit_btn)

        if is_self:
            actions.addStretch()
            you = QLabel("Tú")
            you.setFont(get_font(10, weight=700))
            you.setStyleSheet(NEXAStyles.badge("Tú", SUCCESS))
            actions.addWidget(you)
        else:
            if is_active:
                suspend_btn = _mk_action("Suspender", "close", WARNING, lambda: self._on_toggle_active(user, False))
                actions.addWidget(suspend_btn)
            else:
                activate_btn = _mk_action("Activar", "check", SUCCESS, lambda: self._on_toggle_active(user, True))
                actions.addWidget(activate_btn)
            reset_btn = _mk_action("Contraseña", "refresh", WARNING, lambda: self._on_reset_password(user))
            actions.addWidget(reset_btn)
            del_btn = _mk_action("Eliminar", "close", ERROR, lambda: self._on_delete_user(user))
            actions.addWidget(del_btn)
            actions.addStretch()

        card_layout.addLayout(actions)
        return card

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_add_user(self) -> None:
        if self._auth is None:
            QMessageBox.warning(self, "Sin permisos", "No hay servicio de autenticación.")
            return
        dlg = UserFormDialog(self._auth, self._roles, user=None, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        try:
            new_user = self._auth.create_user(
                username=data["username"], name=data["name"], email=data["email"],
                password=data["password"], area=data.get("area", ""),
                role=data["role"], created_by=self._current_user_id,
            )
            self._audit_user("create", new_user)
            self.data_changed.emit()
            self._reload()
        except Exception as e:  # pragma: no cover
            logger.exception("Error al crear usuario")
            QMessageBox.critical(self, "Error", f"No se pudo crear el usuario: {e}")

    def _on_edit_user(self, user: dict) -> None:
        if self._auth is None:
            return
        dlg = UserFormDialog(self._auth, self._roles, user=user, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        old_role = user.get("roles", ["usuario"])[0] if user.get("roles") else ""
        try:
            updates = {
                "name": data["name"], "email": data["email"],
                "area": data.get("area", ""), "role": data["role"],
            }
            self._auth.update_user(user["id"], **updates)
            if data.get("password"):
                self._auth.reset_password(user["id"], data["password"])
            self._audit_user("update", user, extra={"role_changed": old_role != data["role"]})
            self.data_changed.emit()
            self._reload()
        except Exception as e:  # pragma: no cover
            logger.exception("Error al editar usuario")
            QMessageBox.critical(self, "Error", f"No se pudo editar el usuario: {e}")

    def _on_toggle_active(self, user: dict, activate: bool) -> None:
        verb = "activar" if activate else "suspender"
        reply = QMessageBox.question(
            self, f"{'Activar' if activate else 'Suspender'} usuario",
            f"¿Está seguro de que desea {verb} el usuario '{user.get('name', '')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self._auth.set_active(user["id"], activate):
            self._audit_user("suspend" if not activate else "activate", user)
            self.data_changed.emit()
            self._reload()

    def _on_reset_password(self, user: dict) -> None:
        from PySide6.QtWidgets import QInputDialog
        password, ok = QInputDialog.getText(
            self, "Restablecer contraseña",
            f"Nueva contraseña para '{user.get('username', '')}':",
            QLineEdit.EchoMode.Password,
        )
        if not ok or not password:
            return
        if len(password) < 4:
            QMessageBox.warning(self, "Contraseña débil", "Mínimo 4 caracteres.")
            return
        if self._auth.reset_password(user["id"], password):
            self._audit_user("reset_password", user)
            QMessageBox.information(self, "Listo", "Contraseña restablecida correctamente.")

    def _on_delete_user(self, user: dict) -> None:
        reply = QMessageBox.question(
            self, "Eliminar usuario",
            f"¿Estás seguro de que deseas eliminar este usuario?\n\n'{user.get('name', '')}' (@{user.get('username', '')})\n\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self._auth.delete_user(user["id"]):
            self._audit_user("delete", user)
            self.data_changed.emit()
            self._reload()

    # ------------------------------------------------------------------
    # Auditing + reload
    # ------------------------------------------------------------------
    def _audit_user(self, action: str, user: dict, extra: dict | None = None) -> None:
        if self._audit is None:
            return
        name = user.get("name", user.get("username", ""))
        details = extra or {}
        if action == "create":
            self._audit.log(self._current_user_id, "create", "users", "user", user.get("id", ""), name, details)
        elif action == "update":
            self._audit.log(self._current_user_id, "update", "users", "user", user.get("id", ""), name, details)
        elif action == "delete":
            self._audit.log(self._current_user_id, "delete", "users", "user", user.get("id", ""), name, details)
        elif action == "suspend":
            self._audit.log(self._current_user_id, "suspend", "users", "user", user.get("id", ""), name, details)
        elif action == "activate":
            self._audit.log(self._current_user_id, "activate", "users", "user", user.get("id", ""), name, details)
        elif action == "reset_password":
            self._audit.log(self._current_user_id, "reset_password", "users", "user", user.get("id", ""), name, details)
    def _reload(self) -> None:
        if self._auth is not None:
            users = self._auth.get_all_users(include_inactive=True)
            self.set_users(users)