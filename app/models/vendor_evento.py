"""Eventos de mini-analítica por tienda de vendedor (vistas y clics de WhatsApp).

Registro de eventos crudo (una fila por evento), no contadores
agregados: así no hay que decidir de antemano qué ventanas de tiempo
soportar — `estadisticas_service.resumen_estadisticas` calcula sobre
la marcha lo que haga falta (hoy: últimos `DIAS_VENTANA_ESTADISTICAS`
días). Ver `claude/spec-tiendas-vendedor.md` en el proyecto.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class TipoEventoVendor(str, enum.Enum):
    """Tipo de evento de mini-analítica registrado para una tienda."""

    VISTA = "vista"
    CLIC_WHATSAPP = "clic_whatsapp"


class VendorEvento(db.Model):
    """Un evento puntual (vista de tienda o clic a WhatsApp) de una tienda de vendedor."""

    __tablename__ = "vendor_eventos"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    tipo: Mapped[TipoEventoVendor] = mapped_column(SqlEnum(TipoEventoVendor, name="tipo_evento_vendor"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False, index=True)

    vendor: Mapped["Vendor"] = relationship()
