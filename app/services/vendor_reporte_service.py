"""Reportes de moderación sobre tiendas de vendedor, enviados desde su página pública."""
from __future__ import annotations

from app.extensions import db
from app.models import Vendor, VendorReporte


def crear_reporte(vendor: Vendor, *, motivo: str, contacto: str | None) -> VendorReporte:
    """Guarda un reporte nuevo sobre una tienda.

    Args:
        vendor: Tienda reportada.
        motivo: Texto libre con el motivo del reporte.
        contacto: Email o WhatsApp opcional de quien reporta, para dar seguimiento.

    Returns:
        El `VendorReporte` creado.
    """
    reporte = VendorReporte(vendor_id=vendor.id, motivo=motivo, contacto=contacto)
    db.session.add(reporte)
    db.session.commit()
    return reporte


def listar_reportes_de_vendor(vendor: Vendor) -> list[VendorReporte]:
    """Lista los reportes recibidos por una tienda, más recientes primero.

    Args:
        vendor: Tienda cuyos reportes se listan.

    Returns:
        Lista de `VendorReporte`.
    """
    return (
        VendorReporte.query.filter_by(vendor_id=vendor.id).order_by(VendorReporte.creado_en.desc()).all()
    )
