"""Aviso "avísame cuando vuelva" sobre un producto agotado, desde la tienda pública (`/e-link-aviso`).

Mismo patrón que `reportes.py`: un mini-formulario dentro del modal de
producto (visible solo cuando el estado de stock es "agotado", ver
`vendor_service.resolver_estado_stock_producto`) que cualquier visitante
puede enviar. El producto — y por lo tanto la tienda dueña — se resuelve
del lado del servidor a partir del host de la petición y el
`producto_id` del formulario, nunca de un campo oculto con el vendor_id.
"""
from __future__ import annotations

from flask import Blueprint, abort, current_app, flash, redirect, request

from app.services.auth_service import validar_csrf_token
from app.services.subdominio_service import extraer_slug_de_host
from app.services.vendor_service import (
    AvisoInvalidoError,
    crear_aviso_producto,
    obtener_producto_de_vendor,
    obtener_vendor_por_slug_activo,
)

avisos_bp = Blueprint("avisos", __name__, url_prefix="/e-link-aviso")


@avisos_bp.route("/enviar", methods=["POST"])
def enviar():
    """Recibe el formulario "avísame cuando vuelva" del modal de producto de la tienda pública.

    Returns:
        Redirección de vuelta a la tienda con un flash de confirmación
        (o de error si falta un campo, el producto no existe/no
        pertenece a la tienda de este host, o el token CSRF no es válido).
    """
    if not validar_csrf_token(request.form.get("csrf_token")):
        abort(400, description="Token de seguridad inválido o expirado. Recarga la página e intenta de nuevo.")

    slug = extraer_slug_de_host(request.host, current_app.config["SITE_DOMAIN"])
    vendor = obtener_vendor_por_slug_activo(slug) if slug else None
    if vendor is None:
        abort(404)

    producto_id_raw = request.form.get("producto_id", "")
    producto = (
        obtener_producto_de_vendor(vendor, int(producto_id_raw)) if producto_id_raw.isdigit() else None
    )
    if producto is None:
        abort(404)

    nombre = (request.form.get("nombre") or "").strip()
    contacto = (request.form.get("contacto") or "").strip()
    try:
        crear_aviso_producto(producto, nombre=nombre, contacto=contacto)
    except AvisoInvalidoError as exc:
        flash(str(exc), "error")
        return redirect(request.referrer or "/")

    flash("¡Listo! Te avisamos apenas vuelva a estar disponible.", "success")
    return redirect(request.referrer or "/")
