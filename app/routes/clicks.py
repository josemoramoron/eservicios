"""Redirecciones de clic con registro de mini-analítica (`/e-link-click/...`).

Un `<a href="https://wa.me/...">` directo nunca toca el servidor, así
que no hay forma de contar el clic — este blueprint interpone un
redirect corto: el botón de WhatsApp de la tienda pública apunta acá
en vez de directo a `wa.me`, se registra el evento, y se redirige de
una al destino real. Ver `estadisticas_service.registrar_evento` y
`claude/spec-tiendas-vendedor.md` en el proyecto.
"""
from __future__ import annotations

from flask import Blueprint, abort, current_app, redirect, request

from app.models import TipoEventoVendor
from app.services.estadisticas_service import registrar_evento
from app.services.vendor_service import obtener_vendor_por_slug_activo
from app.services.subdominio_service import extraer_slug_de_host

clicks_bp = Blueprint("clicks", __name__, url_prefix="/e-link-click")

# El destino SIEMPRE debe empezar con este prefijo — si se aceptara
# cualquier URL en `destino` sin validar, este endpoint sería un
# open-redirect (alguien podría armar un link con el dominio de
# eservicios.org que en realidad manda a un sitio de phishing).
_PREFIJO_DESTINO_PERMITIDO = "https://wa.me/"


@clicks_bp.route("/whatsapp")
def click_whatsapp():
    """Registra un clic de WhatsApp de la tienda actual y redirige al chat real.

    El vendedor de la tienda se resuelve del host de la petición (el
    mismo subdominio desde el que se hizo clic), no de un parámetro,
    para no depender de datos que llegan del cliente.

    Returns:
        Redirección 302 al link `wa.me` pedido en `destino`.
    """
    destino = request.args.get("destino", "")
    if not destino.startswith(_PREFIJO_DESTINO_PERMITIDO):
        abort(400)

    slug = extraer_slug_de_host(request.host, current_app.config["SITE_DOMAIN"])
    vendor = obtener_vendor_por_slug_activo(slug) if slug else None
    if vendor is not None:
        registrar_evento(vendor, TipoEventoVendor.CLIC_WHATSAPP)

    return redirect(destino, code=302)
