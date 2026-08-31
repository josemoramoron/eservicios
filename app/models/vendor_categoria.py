"""Modelo de categoría propia del vendedor, para agrupar sus productos.

Distinto de `Category` (el catálogo maestro, curado por el equipo de
eServicios): cada `Vendor` define sus propias categorías, libres, para
organizar y filtrar los productos de SU tienda pública — sin relación
con el catálogo maestro. Función de e-link Plus (roadmap, Fase 2, punto
18). Ver `claude/spec-tiendas-vendedor.md` en el proyecto.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.extensions import db


class VendorCategoria(db.Model):
    """Categoría que el vendedor define para agrupar sus propios productos."""

    __tablename__ = "vendor_categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    orden: Mapped[int] = mapped_column(default=0, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    vendor: Mapped["Vendor"] = relationship(back_populates="categorias")  # noqa: F821
    # Sin cascade: al borrar una categoría, vendor_service.eliminar_categoria
    # pone categoria_id en None a mano en cada producto afectado ANTES de
    # borrar esta fila (ver el comentario en VendorProduct.categoria_id) —
    # los productos nunca se borran por borrar su categoría.
    productos: Mapped[list["VendorProduct"]] = relationship(back_populates="categoria")  # noqa: F821

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el nombre de la categoría.
        """
        return f"<VendorCategoria {self.nombre}>"
