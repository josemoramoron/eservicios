"""Vista de la tienda pública de un vendedor (servida por subdominio).

No es un Blueprint con rutas propias: `renderizar_tienda` se llama
directamente desde el enrutador de subdominios (`before_request` en
`app/__init__.py`), porque la tienda de un vendedor responde en
cualquier ruta de su subdominio (`<slug>.eservicios.org/lo-que-sea`),
no en una sola URL registrada.
"""
from __future__ import annotations

from flask import render_template

from app.models import Vendor
from app.services.iconos_service import detectar_red_social
from app.services.vendor_service import (
    href_whatsapp_producto,
    href_whatsapp_tienda,
    listar_links_activos,
    listar_productos_activos,
)


def renderizar_tienda(vendor: Vendor) -> str:
    """Renderiza la página pública de la tienda de un vendedor.

    Args:
        vendor: Vendedor activo resuelto a partir del host de la petición.

    Returns:
        HTML de la tienda pública.
    """
    productos = listar_productos_activos(vendor)
    productos_con_href = [(producto, href_whatsapp_producto(vendor, producto)) for producto in productos]

    links_con_icono = [(link, detectar_red_social(link.url)) for link in listar_links_activos(vendor)]
    enlaces_redes = [(link, icono) for link, icono in links_con_icono if icono]
    enlaces_otros = [link for link, icono in links_con_icono if not icono]

    return render_template(
        "tienda/publica.html",
        vendor=vendor,
        productos=productos_con_href,
        enlaces_redes=enlaces_redes,
        enlaces_otros=enlaces_otros,
        whatsapp_href_tienda=href_whatsapp_tienda(vendor),
    )
