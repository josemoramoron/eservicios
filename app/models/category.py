"""Modelo de categoría del catálogo de eServicios."""
from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Category(db.Model):
    """Categoría del catálogo (una página de servicios).

    Agrupa varios `Offering` (productos, servicios, cursos o
    consultorías) y define la página pública `/servicios/<slug>`.
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    orden: Mapped[int] = mapped_column(default=0, nullable=False)
    imagen_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    offerings: Mapped[list["Offering"]] = relationship(  # noqa: F821
        back_populates="category", order_by="Offering.nombre"
    )

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el slug de la categoría.
        """
        return f"<Category {self.slug}>"
