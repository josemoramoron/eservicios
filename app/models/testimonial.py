"""Modelo de testimonio de cliente (prueba social, opcional)."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Testimonial(db.Model):
    """Testimonio de un cliente, opcionalmente asociado a un `Offering`."""

    __tablename__ = "testimonials"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente: Mapped[str] = mapped_column(String(150), nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    offering_id: Mapped[int | None] = mapped_column(ForeignKey("offerings.id"), nullable=True)

    offering: Mapped["Offering | None"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el nombre del cliente.
        """
        return f"<Testimonial {self.cliente}>"
