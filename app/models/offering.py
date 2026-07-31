"""Modelo de ítem del catálogo (producto, servicio, curso o consultoría)."""
from __future__ import annotations

import enum
from decimal import Decimal

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class TipoOffering(str, enum.Enum):
    """Tipo de ítem del catálogo."""

    PRODUCTO = "producto"
    SERVICIO = "servicio"
    CURSO = "curso"
    CONSULTORIA = "consultoria"


class Offering(db.Model):
    """Ítem del catálogo: producto, servicio, curso o consultoría.

    Pertenece a una `Category`. Si `vendible` es True se compra por
    carrito/Stripe; si es False, se cotiza vía formulario de contacto
    (`Lead`).
    """

    __tablename__ = "offerings"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    tipo: Mapped[TipoOffering] = mapped_column(
        SqlEnum(TipoOffering, name="tipo_offering"), nullable=False
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    imagen_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    precio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    vendible: Mapped[bool] = mapped_column(default=False, nullable=False)
    stock: Mapped[int | None] = mapped_column(nullable=True)
    destacado: Mapped[bool] = mapped_column(default=False, nullable=False)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)

    category: Mapped["Category"] = relationship(back_populates="offerings")  # noqa: F821

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el slug del ítem.
        """
        return f"<Offering {self.slug}>"
