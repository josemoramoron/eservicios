"""Reporte de tiendas de vendedor desde su página pública (`/e-link-reporte`).

Un formulario en el pie de cada tienda pública permite reportarla — por
ejemplo, si alguien nota que se está usando el número de WhatsApp de
otra persona. La tienda se resuelve del host de la petición (mismo
patrón que `clicks.click_whatsapp`), no de un campo oculto del
formulario, para no depender de datos que llegan del cliente.
"""
from __future__ import annotations

from flask import Blueprint, abort, current_app, flash, redirect, request

from app.services.auth_service import validar_csrf_token
from app.services.subdominio_service import extraer_slug_de_host
from app.services.vendor_reporte_service import crear_reporte
from app.services.vendor_service import obtener_vendor_por_slug_activo

reportes_bp = Blueprint("reportes", __name__, url_prefix="/e-link-reporte")


@reportes_bp.route("/enviar", methods=["POST"])
def enviar():
    """Recibe el formulario de "reportar esta tienda" de la tienda pública.

    Returns:
        Redirección de vuelta a la tienda con un flash de confirmación
        (o de error si falta el motivo o el token CSRF no es válido).
    """
    if not validar_csrf_token(request.form.get("csrf_token")):
        abort(400, description="Token de seguridad inválido o expirado. Recarga la página e intenta de nuevo.")

    slug = extraer_slug_de_host(request.host, current_app.config["SITE_DOMAIN"])
    vendor = obtener_vendor_por_slug_activo(slug) if slug else None
    if vendor is None:
        abort(404)

    motivo = (request.form.get("motivo") or "").strip()
    if not motivo:
        flash("Cuéntanos brevemente el motivo del reporte.", "error")
        return redirect(request.referrer or "/")

    contacto = (request.form.get("contacto") or "").strip() or None
    crear_reporte(vendor, motivo=motivo, contacto=contacto)
    flash("Gracias, recibimos tu reporte y lo vamos a revisar.", "success")
    return redirect(request.referrer or "/")
