"""Solicitud de aviso "avísame cuando vuelva", enviada desde la tienda pública.

Mismo espíritu que `VendorReporte` (formulario público → dueño resuelto
del lado del servidor → registro guardado), pero atado a un producto en
vez de a la tienda entera, y visible solo en el panel del propio
vendedor (no en `/admin`) — es información comercial del vendedor, no
un asunto de moderación. Función de e-link Plus (roadmap, Fase 2, punto
17). Ver `claude/spec-tiendas-vendedor.md` en el proyecto.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.extensions import db


class VendorProductAviso(db.Model):
    """Un pedido de "avísame cuando vuelva" sobre un producto agotado."""

    __tablename__ = "vendor_product_avisos"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_product_id: Mapped[int] = mapped_column(
        ForeignKey("vendor_products.id"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    contacto: Mapped[str] = mapped_column(String(255), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False, index=True)

    producto: Mapped["VendorProduct"] = relationship(back_populates="avisos")  # noqa: F821

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el id del aviso y el id del producto asociado.
        """
        return f"<VendorProductAviso {self.id} producto={self.vendor_product_id}>"
