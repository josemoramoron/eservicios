"""Modelo de vendedor (tienda con subdominio propio, tipo Linktree/Beacons).

Autenticación y perfil de la tienda viven en el mismo modelo, igual que
`AdminUser` — no hace falta separar cuenta de perfil mientras cada
vendedor tenga una sola tienda. El vendedor se registra gratis y elige
el nombre de su subdominio (`slug`, ej. `mitienda.eservicios.org`).
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class PlanVendor(str, enum.Enum):
    """Plan de la tienda del vendedor."""

    FREE = "free"
    # Planes de pago pendientes de definir (ej. PLUS = "plus") — el
    # plan gratis no tiene límites de productos ni fotos por ahora.


class Vendor(db.Model):
    """Vendedor con tienda pública propia en un subdominio (`<slug>.eservicios.org`).

    Corre en paralelo al catálogo maestro (`Category`/`Offering`, curado
    por el equipo de eServicios): cada `Vendor` administra sus propios
    `VendorProduct` y `VendorLink` de forma autogestionada, sin
    moderación por ahora. Ver `claude/spec-tiendas-vendedor.md` en el
    proyecto para el diseño completo.
    """

    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), unique=True, nullable=False, index=True)
    nombre_negocio: Mapped[str] = mapped_column(String(150), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    whatsapp_numero: Mapped[str] = mapped_column(String(30), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    banner_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    plan: Mapped[PlanVendor] = mapped_column(
        SqlEnum(PlanVendor, name="plan_vendor"), default=PlanVendor.FREE, nullable=False
    )
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    productos: Mapped[list["VendorProduct"]] = relationship(  # noqa: F821
        back_populates="vendor", cascade="all, delete-orphan", order_by="VendorProduct.id.desc()"
    )
    links: Mapped[list["VendorLink"]] = relationship(  # noqa: F821
        back_populates="vendor", cascade="all, delete-orphan", order_by="VendorLink.orden"
    )
    slugs_anteriores: Mapped[list["VendorSlugHistorial"]] = relationship(  # noqa: F821
        back_populates="vendor",
        cascade="all, delete-orphan",
        order_by="VendorSlugHistorial.creado_en.desc()",
    )

    def set_password(self, password: str) -> None:
        """Genera y guarda el hash de una contraseña nueva.

        Args:
            password: Contraseña en texto plano a hashear.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifica una contraseña contra el hash guardado.

        Args:
            password: Contraseña en texto plano a verificar.

        Returns:
            True si la contraseña coincide con el hash guardado.
        """
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el slug de la tienda.
        """
        return f"<Vendor {self.slug}>"
