"""Modelo de palabras reservadas de subdominio (no disponibles para vendedores)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.extensions import db


class ReservedSlug(db.Model):
    """Palabra reservada que ningún `Vendor` puede usar como subdominio.

    Editable desde el panel de administración (no solo en código) para
    poder ampliar la lista sin necesidad de un deploy — ver el listado
    inicial en `scripts/seed_reserved_slugs.py`.
    """

    __tablename__ = "reserved_slugs"

    id: Mapped[int] = mapped_column(primary_key=True)
    palabra: Mapped[str] = mapped_column(String(63), unique=True, nullable=False, index=True)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con la palabra reservada.
        """
        return f"<ReservedSlug {self.palabra}>"
