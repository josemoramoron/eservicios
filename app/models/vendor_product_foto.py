"""Modelo de foto adicional de un producto de vendedor (galería, hasta 5)."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class VendorProductFoto(db.Model):
    """Una foto de la galería de un `VendorProduct` (además de su portada).

    `VendorProduct.foto_url` sigue siendo la portada (miniatura de la
    tarjeta en la tienda pública) — se mantiene sincronizada como la
    primera foto de esta galería, ver `vendor_service._establecer_fotos_producto`.
    Esta tabla es la que permite hasta `MAX_FOTOS_PRODUCTO` fotos por
    producto en el modal de detalle de la tienda.
    """

    __tablename__ = "vendor_product_fotos"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_product_id: Mapped[int] = mapped_column(
        ForeignKey("vendor_products.id"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    orden: Mapped[int] = mapped_column(default=0, nullable=False)

    producto: Mapped["VendorProduct"] = relationship(back_populates="fotos")  # noqa: F821

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el id de la foto y el producto al que pertenece.
        """
        return f"<VendorProductFoto {self.id} de producto {self.vendor_product_id}>"
