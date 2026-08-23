"""Modelo de producto subido por un vendedor a su propia tienda."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.extensions import db


class VendorProduct(db.Model):
    """Producto que un vendedor sube a su propia tienda (`Vendor`).

    Sin moderación por ahora: se publica de inmediato al crearse
    (`activo=True` por defecto). Precio siempre en USD — no hay
    selector de moneda en esta primera versión.
    """

    __tablename__ = "vendor_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    foto_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    vendor: Mapped["Vendor"] = relationship(back_populates="productos")  # noqa: F821

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el id y el título del producto.
        """
        return f"<VendorProduct {self.id} {self.titulo}>"
