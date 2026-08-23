"""Autenticación de vendedores (tiendas con subdominio propio, `/vendedor`).

Sesión basada en la cookie firmada de Flask, igual que
`app/services/auth_service.py` para el panel de administración — pero
separada por completo: un `Vendor` autenticado NUNCA implica un
`AdminUser` autenticado, y viceversa (`session` usa una clave distinta
para cada uno). Reutiliza el token CSRF genérico de `auth_service`
(no es específico del panel de admin, solo vive ahí históricamente).

Nota sobre el principio de "el sitio no tiene cuentas de cliente" del
resto de `eServicios` (ver `admin_user.py`): sigue siendo cierto para
el checkout del catálogo maestro (invitado, vía `Order.email`). Los
`Vendor` son un tipo de cuenta distinto — vendedores autogestionando
su propia tienda — introducido específicamente por este feature.
"""
from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import flash, redirect, request, session, url_for

from app.extensions import db
from app.models import Vendor

_SESSION_KEY = "vendor_id"


def autenticar_vendor(email: str, password: str) -> Vendor | None:
    """Verifica credenciales de un `Vendor`.

    Args:
        email: Correo ingresado en el formulario de login.
        password: Contraseña en texto plano ingresada en el formulario.

    Returns:
        El `Vendor` si las credenciales son correctas y la tienda está
        activa, None si no.
    """
    email_normalizado = email.strip().lower()
    if not email_normalizado or not password:
        return None
    vendor = Vendor.query.filter_by(email=email_normalizado).first()
    if vendor is None or not vendor.activo or not vendor.check_password(password):
        return None
    return vendor


def iniciar_sesion_vendor(vendor: Vendor) -> None:
    """Guarda el id del vendedor autenticado en la sesión de Flask.

    Args:
        vendor: Vendedor que acaba de autenticarse o registrarse.
    """
    session.pop("admin_id", None)  # por si el mismo navegador tenía sesión de admin
    session[_SESSION_KEY] = vendor.id


def cerrar_sesion_vendor() -> None:
    """Elimina los datos de sesión del vendedor."""
    session.pop(_SESSION_KEY, None)


def vendor_actual() -> Vendor | None:
    """Devuelve el `Vendor` de la sesión activa, si hay una.

    Returns:
        El vendedor autenticado, o None si no hay sesión activa.
    """
    vendor_id = session.get(_SESSION_KEY)
    if vendor_id is None:
        return None
    return db.session.get(Vendor, vendor_id)


def requiere_vendor(vista: Callable) -> Callable:
    """Decorador que exige una sesión de vendedor activa.

    Redirige a `/vendedor/login` si no hay sesión, guardando la URL
    solicitada para volver ahí después de iniciar sesión.

    Args:
        vista: Función de vista Flask a proteger.

    Returns:
        La vista envuelta con el chequeo de sesión.
    """

    @wraps(vista)
    def vista_protegida(*args, **kwargs):
        if vendor_actual() is None:
            flash("Inicia sesión para continuar.", "error")
            return redirect(url_for("vendedor.login", next=request.path))
        return vista(*args, **kwargs)

    return vista_protegida
