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
from app.services.vendor_service import (
    construir_mensaje_consulta_multiple,
    construir_whatsapp_href,
    listar_productos_activos,
    obtener_vendor_por_slug_activo,
    resolver_consulta_multiple_habilitada,
)
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


@clicks_bp.route("/whatsapp-multiple")
def click_whatsapp_multiple():
    """Arma y redirige a un mensaje de WhatsApp combinado de varios productos.

    Punto 19 del roadmap (Fase 2, e-link Plus) — "consulta de múltiples
    productos". El cliente marca productos en la tienda pública (sin
    recargar la página, ver `static/js/consulta_multiple.js`) y este
    endpoint arma el link real: recibe solo IDS en `productos` (nunca los
    títulos ni el mensaje ya armado, para que el texto final salga
    siempre del servidor, igual que `href_whatsapp_tienda`/
    `href_whatsapp_producto` — ver `.clinerules`, nada de lógica de
    negocio en el cliente).

    Seguridad, mismo criterio que `click_whatsapp` y `avisos.enviar`: la
    tienda se resuelve del host de la petición, nunca de un parámetro, y
    los ids recibidos se filtran contra los productos activos de ESA
    tienda — un id que no pertenezca al vendedor (o que ya no exista) se
    descarta en silencio en vez de fallar, así un carrito con un producto
    borrado justo antes de hacer clic no rompe toda la consulta.

    Returns:
        Redirección 302 al link `wa.me` combinado. 400 si el vendedor no
        tiene Plus vigente (la función está gateada, ver
        `resolver_consulta_multiple_habilitada`), o si no queda ningún
        producto válido tras filtrar `productos`.
    """
    slug = extraer_slug_de_host(request.host, current_app.config["SITE_DOMAIN"])
    vendor = obtener_vendor_por_slug_activo(slug) if slug else None
    if vendor is None or not resolver_consulta_multiple_habilitada(vendor):
        abort(400)

    ids_pedidos = [
        int(id_texto) for id_texto in request.args.get("productos", "").split(",") if id_texto.strip().isdigit()
    ]
    productos_por_id = {producto.id: producto for producto in listar_productos_activos(vendor)}
    # Se conserva el orden en el que el cliente los marcó (ids_pedidos),
    # no el orden del catálogo — más intuitivo para quien arma el mensaje.
    productos_seleccionados = [productos_por_id[id_] for id_ in ids_pedidos if id_ in productos_por_id]
    if not productos_seleccionados:
        abort(400)

    mensaje = construir_mensaje_consulta_multiple(vendor, productos_seleccionados)
    destino = construir_whatsapp_href(vendor.whatsapp_numero, mensaje)

    registrar_evento(vendor, TipoEventoVendor.CLIC_WHATSAPP)
    return redirect(destino, code=302)
