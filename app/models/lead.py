"""Modelo de solicitud de contacto/cotización."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.extensions import db


class Lead(db.Model):
    """Solicitud de contacto o cotización enviada desde el sitio.

    Se usa para ítems no vendibles directamente (`Offering.vendible`
    en False) o para el formulario general de contacto, en cuyo caso
    `offering_id` queda nulo.
    """

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    offering_id: Mapped[int | None] = mapped_column(ForeignKey("offerings.id"), nullable=True)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    atendido: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    offering: Mapped["Offering | None"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el id y el email del lead.
        """
        return f"<Lead {self.id} {self.email}>"
