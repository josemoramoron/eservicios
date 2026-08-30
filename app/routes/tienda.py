"""Vista de la tienda pública de un vendedor (servida por subdominio).

No es un Blueprint con rutas propias: `renderizar_tienda` se llama
directamente desde el enrutador de subdominios (`before_request` en
`app/__init__.py`), porque la tienda de un vendedor responde en
cualquier ruta de su subdominio (`<slug>.eservicios.org/lo-que-sea`),
no en una sola URL registrada.
"""
from __future__ import annotations

from flask import current_app, make_response, render_template, request, url_for

from app.models import TipoEventoVendor, Vendor
from app.services.auth_service import generar_csrf_token
from app.services.estadisticas_service import registrar_evento
from app.services.estilos_portada_service import obtener_preset_portada
from app.services.iconos_service import detectar_red_social
from app.services.vendor_service import (
    href_whatsapp_producto,
    href_whatsapp_tienda,
    listar_links_activos,
    listar_productos_activos,
    resolver_acento_vendor,
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


def _href_dominio_principal(endpoint: str) -> str:
    """Arma una URL absoluta al dominio principal para un endpoint dado.

    Un `url_for` normal genera una ruta relativa que, al hacer clic
    desde el subdominio de una tienda, seguiría resolviendo contra ese
    mismo subdominio (el `before_request` de subdominios la volvería a
    interceptar y mostraría la tienda de nuevo en vez de la página
    pedida) — mismo problema que ya resuelve `url_login` en
    `enrutar_subdominio_vendedor`.

    Args:
        endpoint: Nombre del endpoint de Flask (ej. "legal.terminos").

    Returns:
        URL absoluta al dominio principal.
    """
    puerto = f":{request.host.split(':', 1)[1]}" if ":" in request.host else ""
    return f"{request.scheme}://{current_app.config['SITE_DOMAIN']}{puerto}{url_for(endpoint)}"


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

    # Todos los enlaces se pintan como botón circular: una red reconocida
    # muestra su ícono de marca (ver `iconos_service.detectar_red_social`);
    # cualquier otro sitio muestra la inicial del título del enlace en vez
    # de un ícono (resuelto en el template) — ya no existe la variante
    # "pastilla" con texto para las no reconocidas.
    enlaces = [(link, detectar_red_social(link.url)) for link in listar_links_activos(vendor)]

    # El color de acento propio (e-link Plus, punto 12 del roadmap) gana
    # sobre la galería de estilos prediseñados (punto 26, gratis) cuando
    # ambos están elegidos — por eso el preset ni se resuelve si hay
    # acento activo: el fallback en tienda.css (var(--color-portada-inicio,
    # var(--color-accent))) ya cae solo en el acento del vendedor.
    acento = resolver_acento_vendor(vendor)
    preset_portada = None if acento else obtener_preset_portada(vendor.estilo_portada)

    respuesta = make_response(
        render_template(
            "tienda/publica.html",
            vendor=vendor,
            productos=productos_con_href,
            enlaces=enlaces,
            whatsapp_href_tienda=_href_click(href_whatsapp_tienda(vendor)),
            terminos_href=_href_dominio_principal("legal.terminos"),
            csrf_token=generar_csrf_token,
            preset_portada=preset_portada,
            acento=acento,
        )
    )
    respuesta.headers["Cache-Control"] = _CACHE_CONTROL_TIENDA
    return respuesta
