"""Links de WhatsApp prellenados y el vCard de la tienda.

Extraído de vendor_service.py (bloque "WhatsApp/vCard" del split de
god-files, 2026-09-25). Toda la construcción de mensajes de WhatsApp y
del archivo .vcf vive acá — templates y JS nunca arman texto, solo lo
muestran (ver `.clinerules`).
"""
from __future__ import annotations

import re
from urllib.parse import quote

from app.models import Vendor, VendorProduct
from app.services.site_info_service import obtener_info_sitio
from app.services.vendor_perfil_service import plan_plus_o_prueba_vigente


def construir_whatsapp_href(numero: str, mensaje: str) -> str:
    """Arma un link `wa.me` con mensaje prellenado.

    Toda la lógica de codificación de URL vive aquí a propósito — los
    templates de eServicios no llevan lógica Python, solo la muestran.

    Args:
        numero: Número de WhatsApp del vendedor (con código de país).
        mensaje: Texto a prellenar en el chat.

    Returns:
        URL lista para usar en un `<a href>`.
    """
    return f"https://wa.me/{numero}?text={quote(mensaje)}"


def _membrete_trazabilidad(vendor: Vendor) -> str:
    """Firma que se agrega al final de todo mensaje de WhatsApp armado desde una tienda.

    Deja un rastro de qué tienda de e-link originó el mensaje — si
    alguien usa el número de WhatsApp de otra persona sin autorización,
    esta firma facilita identificar desde qué subdominio salió el
    contacto (ver también `reportes.enviar`, el "reportar este sitio"
    de la tienda pública).

    Args:
        vendor: Tienda desde la que se arma el mensaje.

    Returns:
        Línea de firma lista para concatenar al mensaje.
    """
    return f"\n\n— vía {vendor.slug}.eservicios.org"


def href_whatsapp_tienda(vendor: Vendor) -> str:
    """Link de WhatsApp general de la tienda (botón del encabezado).

    Args:
        vendor: Tienda para la que se arma el link.

    Returns:
        URL `wa.me` con un mensaje genérico y el membrete de trazabilidad.
    """
    return construir_whatsapp_href(
        vendor.whatsapp_numero,
        f"Hola, tengo una consulta sobre {vendor.nombre_negocio}.{_membrete_trazabilidad(vendor)}",
    )


def href_whatsapp_producto(vendor: Vendor, producto: VendorProduct) -> str:
    """Link de WhatsApp de un producto puntual (botón del detalle).

    Args:
        vendor: Tienda dueña del producto.
        producto: Producto sobre el que se pregunta.

    Returns:
        URL `wa.me` con el nombre del producto y el membrete de trazabilidad.
    """
    return construir_whatsapp_href(
        vendor.whatsapp_numero,
        f'Hola, quiero info sobre "{producto.titulo}" en {vendor.nombre_negocio}.'
        f"{_membrete_trazabilidad(vendor)}",
    )


def href_whatsapp_soporte_pago() -> str:
    """Link de WhatsApp de soporte de eServicios para dudas de pago de e-link Plus.

    Se usa en `/vendedor/perfil/plan/solicitar` mientras los métodos de
    pago propios siguen "por definir" (2026-09-14, pedido de Jose):
    reutiliza el mismo número de contacto general de eServicios (ver
    `site_info_service.obtener_info_sitio`, el mismo del botón flotante
    y el pie de página en `base.html`), no el `whatsapp_numero` del
    vendedor — esta pregunta es para el equipo de eServicios, no para
    la tienda del vendedor.

    Returns:
        URL `wa.me` lista para usar en un `<a href>`.
    """
    numero = re.sub(r"\D", "", obtener_info_sitio().contacto.whatsapp_numero)
    return construir_whatsapp_href(
        numero,
        "Hola, quiero consultar los métodos de pago disponibles para e-link Plus.",
    )


def resolver_consulta_multiple_habilitada(vendor: Vendor) -> bool:
    """Indica si el vendedor puede usar la consulta combinada de varios productos.

    Punto 19 del roadmap (Fase 2, e-link Plus) — "el cliente marca varios
    productos y se genera un solo mensaje de WhatsApp combinado". A
    diferencia de `moneda`/`verificado` (gratis para cualquier plan), este
    punto se quedó con la clasificación por defecto del roadmap (Premium):
    Jose no pidió ningún override explícito para él, así que sigue el
    mismo patrón que color de acento/plantillas/badges/estado de
    stock/categorías — gateado por `plan_plus_o_prueba_vigente()`
    (cuenta la prueba gratuita de 7 días, 2026-09-14).

    A diferencia de esos otros puntos, esta función no tiene ningún valor
    que "guardar siempre" — no es una preferencia del vendedor, es una
    capacidad de la tienda que está activa o no según el plan en cada
    momento. Por eso no hay ninguna columna nueva en `Vendor` para esto.

    Args:
        vendor: Tienda a evaluar.

    Returns:
        True si Plus (real o de prueba) está vigente en este momento.
    """
    return plan_plus_o_prueba_vigente(vendor)


def construir_mensaje_consulta_multiple(vendor: Vendor, productos: list[VendorProduct]) -> str:
    """Arma el texto del mensaje de WhatsApp combinado para varios productos.

    Mismo criterio que `href_whatsapp_tienda`/`href_whatsapp_producto`: la
    construcción del texto vive enteramente en el servicio, nunca en el
    template ni en JavaScript — el cliente solo elige QUÉ productos
    marcar (mandando sus ids a `clicks.click_whatsapp_multiple`), nunca
    arma el mensaje él mismo.

    Args:
        vendor: Tienda dueña de los productos.
        productos: Productos seleccionados, ya validados como activos y
            pertenecientes a esta tienda (ver `clicks.click_whatsapp_multiple`).
            No puede venir vacía — se asume que el llamador ya filtró la
            lista antes de invocar esta función.

    Returns:
        Texto completo del mensaje, con un producto por línea y el
        membrete de trazabilidad al final.
    """
    lineas_productos = "\n".join(f"- {producto.titulo}" for producto in productos)
    return (
        f"Hola, quiero consultar sobre estos productos en {vendor.nombre_negocio}:\n"
        f"{lineas_productos}"
        f"{_membrete_trazabilidad(vendor)}"
    )


def _escapar_texto_vcard(texto: str) -> str:
    """Escapa los caracteres especiales del formato vCard (backslash, punto y coma, coma, salto de línea).

    Args:
        texto: Texto sin escapar.

    Returns:
        El texto listo para insertarse en un campo de una línea vCard.
    """
    return texto.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def construir_vcard(vendor: Vendor) -> str:
    """Arma el contenido de un archivo vCard (.vcf) con los datos públicos de la tienda.

    Pensado para que el vendedor lo descargue junto al QR (ver
    `/vendedor/contacto.vcf`) y lo comparta para que sus clientes
    guarden la tienda como contacto de un toque, sin escribir el
    número a mano.

    Args:
        vendor: Tienda cuyo contacto se exporta.

    Returns:
        Texto en formato vCard 3.0, listo para escribir a un archivo `.vcf`.
    """
    lineas = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{_escapar_texto_vcard(vendor.nombre_negocio)}",
        f"ORG:{_escapar_texto_vcard(vendor.nombre_negocio)}",
        f"TEL;TYPE=CELL:{vendor.whatsapp_numero}",
        f"URL:https://{vendor.slug}.eservicios.org",
    ]
    if vendor.bio:
        lineas.append(f"NOTE:{_escapar_texto_vcard(vendor.bio)}")
    lineas.append("END:VCARD")
    return "\r\n".join(lineas)

