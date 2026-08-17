"""Modelo de artículo del blog de noticias."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.extensions import db


class EstadoBlogPost(str, enum.Enum):
    """Estado de publicación de un artículo del blog."""

    BORRADOR = "borrador"
    PUBLICADO = "publicado"


class BlogPost(db.Model):
    """Artículo del blog de noticias (`/blog`).

    El contenido se escribe en Markdown desde el panel de administración
    y se convierte a HTML al mostrarlo en el sitio público
    (`app/services/blog_service.py::render_markdown`).
    """

    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    resumen: Mapped[str | None] = mapped_column(String(300), nullable=True)
    contenido_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    imagen_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado: Mapped[EstadoBlogPost] = mapped_column(
        SqlEnum(EstadoBlogPost, name="estado_blog_post"), default=EstadoBlogPost.BORRADOR, nullable=False
    )
    publicado_en: Mapped[datetime | None] = mapped_column(nullable=True)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el slug del artículo.
        """
        return f"<BlogPost {self.slug}>"
