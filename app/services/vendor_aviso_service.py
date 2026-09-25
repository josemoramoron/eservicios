"""Avisos "avísame cuando vuelva" sobre productos agotados.

Extraído de vendor_service.py (bloque "Avisos de producto" del split de
god-files, 2026-09-25) — dos funciones sin dependencias cruzadas hacia el
resto de vendor_service.py.
"""
from __future__ import annotations

from app.extensions import db
from app.models import Vendor, VendorProduct, VendorProductAviso


class AvisoInvalidoError(Exception):
    """El nombre o el contacto del aviso "avísame cuando vuelva" no son válidos."""


def crear_aviso_producto(producto: VendorProduct, *, nombre: str, contacto: str) -> VendorProductAviso:
    """Guarda un pedido de "avísame cuando vuelva" sobre un producto agotado.

    El producto (y por lo tanto la tienda dueña) se resuelve del lado
    del servidor a partir del `product_id` recibido por la ruta pública
    — nunca de un campo oculto del formulario — mismo criterio de
    seguridad que `vendor_reporte_service.crear_reporte` usa para el
    `vendor_id`. Esta función en sí no vuelve a validar eso: asume que
    el llamador (la ruta) ya resolvió `producto` de forma confiable.

    Args:
        producto: Producto sobre el que se pide el aviso.
        nombre: Nombre de quien pide el aviso.
        contacto: Email o WhatsApp de quien pide el aviso, para avisarle.

    Returns:
        El `VendorProductAviso` creado.

    Raises:
        AvisoInvalidoError: Si el nombre o el contacto quedan vacíos.
    """
    nombre = nombre.strip()
    contacto = contacto.strip()
    if not nombre:
        raise AvisoInvalidoError("El nombre es obligatorio.")
    if not contacto:
        raise AvisoInvalidoError("El contacto es obligatorio.")
    aviso = VendorProductAviso(vendor_product_id=producto.id, nombre=nombre, contacto=contacto)
    db.session.add(aviso)
    db.session.commit()
    return aviso


def listar_avisos_de_vendor(vendor: Vendor) -> list[VendorProductAviso]:
    """Lista los avisos "avísame cuando vuelva" recibidos por todos los productos de una tienda.

    Visible solo en el panel del propio vendedor (no en `/admin`) — es
    información comercial del vendedor, no un asunto de moderación.

    Args:
        vendor: Tienda cuyos avisos se listan.

    Returns:
        Lista de `VendorProductAviso` de todos los productos de `vendor`,
        más recientes primero.
    """
    return (
        VendorProductAviso.query.join(VendorProduct)
        .filter(VendorProduct.vendor_id == vendor.id)
        .order_by(VendorProductAviso.creado_en.desc())
        .all()
    )
