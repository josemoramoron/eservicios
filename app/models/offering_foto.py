"""Modelo de foto adicional de una oferta del catálogo (galería de detalle)."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class OfferingFoto(db.Model):
    """Foto adicional de la galería de una `Offering`.

    Independiente de `Offering.imagen_url` (que sigue siendo la
    miniatura/portada usada en la grilla de categoría, el slider de
    inicio y las metaetiquetas Open Graph) — estas son las fotos que se
    muestran en la galería de la ficha de detalle, hasta
    `catalogo_service.MAX_FOTOS_OFERTA` por oferta.
    """

    __tablename__ = "offering_fotos"

    id: Mapped[int] = mapped_column(primary_key=True)
    offering_id: Mapped[int] = mapped_column(ForeignKey("offerings.id"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    orden: Mapped[int] = mapped_column(default=0, nullable=False)

    offering: Mapped["Offering"] = relationship(back_populates="fotos")  # noqa: F821

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el id de la oferta dueña de la foto.
        """
        return f"<OfferingFoto oferta={self.offering_id}>"
