"""Mini-analítica de tiendas de vendedor: vistas y clics de WhatsApp.

Deliberadamente simple (sin panel de fechas, sin exportar CSV, sin
segmentar por producto): el objetivo es darle al vendedor una señal
rápida de "¿esto se está viendo?", no un dashboard de analítica
completo. Ver `claude/spec-tiendas-vendedor.md` en el proyecto.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.extensions import db
from app.models import TipoEventoVendor, Vendor, VendorEvento

# Ventana de tiempo que resume `resumen_estadisticas` — no hay
# selector de rango a propósito, ver docstring del módulo.
DIAS_VENTANA_ESTADISTICAS = 30


def registrar_evento(vendor: Vendor, tipo: TipoEventoVendor) -> None:
    """Registra un evento de mini-analítica para una tienda, sin interrumpir la petición si falla.

    Se llama desde la tienda pública (vista de página, clic a
    WhatsApp) — un error acá (ej. la base de datos momentáneamente
    ocupada) nunca debe tumbar la carga de la tienda ni el redirect a
    WhatsApp, así que cualquier excepción se traga después de revertir
    la sesión.

    Args:
        vendor: Tienda a la que pertenece el evento.
        tipo: Tipo de evento (`TipoEventoVendor.VISTA` o `CLIC_WHATSAPP`).
    """
    try:
        db.session.add(VendorEvento(vendor_id=vendor.id, tipo=tipo))
        db.session.commit()
    except Exception:
        db.session.rollback()


def resumen_estadisticas(vendor: Vendor) -> dict:
    """Resume las vistas y clics de WhatsApp de una tienda en los últimos días.

    Args:
        vendor: Tienda a resumir.

    Returns:
        Diccionario con `vistas` (int), `clics_whatsapp` (int), y
        `dias` (la ventana usada, `DIAS_VENTANA_ESTADISTICAS`) — pensado
        para pintarse directo en las tarjetas `.admin-stat-card` del
        dashboard del vendedor.
    """
    desde = datetime.utcnow() - timedelta(days=DIAS_VENTANA_ESTADISTICAS)
    base = VendorEvento.query.filter(
        VendorEvento.vendor_id == vendor.id, VendorEvento.creado_en >= desde
    )
    return {
        "vistas": base.filter(VendorEvento.tipo == TipoEventoVendor.VISTA).count(),
        "clics_whatsapp": base.filter(VendorEvento.tipo == TipoEventoVendor.CLIC_WHATSAPP).count(),
        "dias": DIAS_VENTANA_ESTADISTICAS,
    }
