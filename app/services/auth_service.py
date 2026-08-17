"""Autenticación y protección del panel de administración (`/admin`).

Sesión basada en la cookie firmada de Flask (usa `SECRET_KEY`, ya
configurada) — no hay cuentas de cliente en el sitio, esto es solo
para el equipo de eServicios. Incluye un token CSRF casero (sin
dependencias nuevas) para los formularios que escriben en la base
de datos.
"""
from __future__ import annotations

import secrets
from functools import wraps
from typing import Callable

from flask import flash, redirect, request, session, url_for

from app.extensions import db
from app.models import AdminUser

_SESSION_KEY = "admin_id"


def autenticar(email: str, password: str) -> AdminUser | None:
    """Verifica credenciales de un `AdminUser`.

    Args:
        email: Correo ingresado en el formulario de login.
        password: Contraseña en texto plano ingresada en el formulario.

    Returns:
        El `AdminUser` si las credenciales son correctas, None si no.
    """
    email_normalizado = email.strip().lower()
    if not email_normalizado or not password:
        return None
    admin = AdminUser.query.filter_by(email=email_normalizado).first()
    if admin is None or not admin.check_password(password):
        return None
    return admin


def iniciar_sesion_admin(admin: AdminUser) -> None:
    """Guarda el id del admin autenticado en la sesión de Flask.

    Args:
        admin: Administrador que acaba de autenticarse.
    """
    session.clear()
    session[_SESSION_KEY] = admin.id


def cerrar_sesion_admin() -> None:
    """Elimina los datos de sesión del panel de administración."""
    session.pop(_SESSION_KEY, None)


def admin_actual() -> AdminUser | None:
    """Devuelve el `AdminUser` de la sesión activa, si hay una.

    Returns:
        El administrador autenticado, o None si no hay sesión activa.
    """
    admin_id = session.get(_SESSION_KEY)
    if admin_id is None:
        return None
    return db.session.get(AdminUser, admin_id)


def requiere_admin(vista: Callable) -> Callable:
    """Decorador que exige una sesión de administrador activa.

    Redirige a `/admin/login` si no hay sesión, guardando la URL
    solicitada para volver ahí después de iniciar sesión.

    Args:
        vista: Función de vista Flask a proteger.

    Returns:
        La vista envuelta con el chequeo de sesión.
    """

    @wraps(vista)
    def vista_protegida(*args, **kwargs):
        if admin_actual() is None:
            flash("Inicia sesión para continuar.", "error")
            return redirect(url_for("admin.login", next=request.path))
        return vista(*args, **kwargs)

    return vista_protegida


def generar_csrf_token() -> str:
    """Genera (o reutiliza) el token CSRF de la sesión actual.

    Returns:
        Token CSRF a incrustar como campo oculto en los formularios.
    """
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validar_csrf_token(token: str | None) -> bool:
    """Valida un token CSRF recibido contra el guardado en sesión.

    Args:
        token: Token recibido en el campo oculto del formulario.

    Returns:
        True si coincide con el de la sesión.
    """
    return bool(token) and secrets.compare_digest(token, session.get("csrf_token", ""))
