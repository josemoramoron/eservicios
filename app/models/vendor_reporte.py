"""Reporte de una tienda de vendedor, enviado desde su página pública.

Registro simple de moderación: cualquier visitante de una tienda puede
reportarla (por ejemplo, si sospecha que se está usando el número de
WhatsApp de otra persona). No hay flujo de resolución todavía — el
equipo de eServicios los revisa desde el detalle del vendedor en el
panel de admin. Ver `claude/spec-tiendas-vendedor.md` en el proyecto.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.extensions import db


class VendorReporte(db.Model):
    """Un reporte de moderación sobre una tienda de vendedor."""

    __tablename__ = "vendor_reportes"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    contacto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False, index=True)

    vendor: Mapped["Vendor"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el id del reporte y el id de la tienda reportada.
        """
        return f"<VendorReporte {self.id} vendor={self.vendor_id}>"
