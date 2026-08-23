"""Modelo de enlace personalizado del vendedor (estilo Linktree)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.extensions import db


class VendorLink(db.Model):
    """Enlace externo que el vendedor agrega a su tienda pública.

    Además de sus productos, el vendedor puede listar enlaces a otras
    redes o sitios (Instagram, TikTok, su propio sitio web, etc.),
    igual que en Linktree/Beacons/Taplink — se muestran como una lista
    de botones en `tienda/publica.html`, antes de la grilla de productos.
    """

    __tablename__ = "vendor_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(80), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    orden: Mapped[int] = mapped_column(default=0, nullable=False)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    vendor: Mapped["Vendor"] = relationship(back_populates="links")  # noqa: F821

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el título del enlace.
        """
        return f"<VendorLink {self.titulo}>"
