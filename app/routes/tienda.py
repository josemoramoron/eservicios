"""Vista de la tienda pública de un vendedor (servida por subdominio).

No es un Blueprint con rutas propias: `renderizar_tienda` se llama
directamente desde el enrutador de subdominios (`before_request` en
`app/__init__.py`), porque la tienda de un vendedor responde en
cualquier ruta de su subdominio (`<slug>.eservicios.org/lo-que-sea`),
no en una sola URL registrada.
"""
from __future__ import annotations

from flask import make_response, render_template, url_for

from app.models import TipoEventoVendor, Vendor
from app.services.estadisticas_service import registrar_evento
from app.services.iconos_service import detectar_red_social
from app.services.vendor_service import (
    href_whatsapp_producto,
    href_whatsapp_tienda,
    listar_links_activos,
    listar_productos_activos,
)

# La tienda pública se sirve con este `Cache-Control` (navegador y
# Cloudflare) — 60 segundos es suficiente para aliviar la carga de
# peticiones repetidas sin que un cambio reciente (nuevo producto,
# perfil actualizado) tarde demasiado en verse.
_CACHE_CONTROL_TIENDA = "public, max-age=60"


def _href_click(url_destino: str) -> str:
    """Envuelve un link `wa.me` con el redirect de `/e-link-click/whatsapp` para contarlo.

    Args:
        url_destino: URL `wa.me` real generada por `vendor_service`.

    Returns:
        URL de `clicks.click_whatsapp` con `destino` como parámetro.
    """
    return url_for("clicks.click_whatsapp", destino=url_destino)


def renderizar_tienda(vendor: Vendor):
    """Renderiza la página pública de la tienda de un vendedor.

    Registra una vista de mini-analítica (ver `estadisticas_service`)
    y agrega el header `Cache-Control` a la respuesta.

    Args:
        vendor: Vendedor activo resuelto a partir del host de la petición.

    Returns:
        Respuesta Flask con el HTML de la tienda pública.
    """
    registrar_evento(vendor, TipoEventoVendor.VISTA)

    productos = listar_productos_activos(vendor)
    productos_con_href = [
        (producto, _href_click(href_whatsapp_producto(vendor, producto))) for producto in productos
    ]

    links_con_icono = [(link, detectar_red_social(link.url)) for link in listar_links_activos(vendor)]
    enlaces_redes = [(link, icono) for link, icono in links_con_icono if icono]
    enlaces_otros = [link for link, icono in links_con_icono if not icono]

    respuesta = make_response(
        render_template(
            "tienda/publica.html",
            vendor=vendor,
            productos=productos_con_href,
            enlaces_redes=enlaces_redes,
            enlaces_otros=enlaces_otros,
            whatsapp_href_tienda=_href_click(href_whatsapp_tienda(vendor)),
        )
    )
    respuesta.headers["Cache-Control"] = _CACHE_CONTROL_TIENDA
    return respuesta
