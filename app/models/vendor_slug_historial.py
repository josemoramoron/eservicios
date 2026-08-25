"""Historial de subdominios (slugs) anteriores de un vendedor.

Se crea una fila cada vez que un vendedor cambia el subdominio de su
tienda (ver `vendor_service.cambiar_slug`). Cumple dos funciones: (1)
mientras `expira_en` no haya pasado, el slug anterior sigue
redirigiendo automáticamente al slug nuevo (`subdominio_service.
resolver_redireccion_slug_antiguo`), para no romper enlaces que el
vendedor ya haya compartido; y (2) mientras esté vigente, reserva ese
slug para que ningún otro vendedor lo pueda tomar mientras la
redirección siga activa (`vendor_service.slug_disponible`). También
sirve para contar cuántas veces ya cambió de slug (límite de
`vendor_service.MAX_CAMBIOS_SLUG`) y desde cuándo puede volver a
cambiarlo (`vendor_service.DIAS_ENTRE_CAMBIOS_SLUG`). Ver
`claude/spec-tiendas-vendedor.md` en el proyecto para el diseño completo.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.extensions import db


class VendorSlugHistorial(db.Model):
    """Un slug anterior de un vendedor, con la fecha en que deja de redirigir.

    A propósito `slug_anterior` NO tiene una restricción `unique` a
    nivel de base de datos: una vez que `expira_en` queda en el pasado,
    ese mismo texto de slug debe poder reutilizarse libremente (por el
    mismo vendedor en un cambio futuro, o por cualquier otro) sin chocar
    con esta fila vieja que ya no bloquea nada. La vigencia se controla
    siempre comparando `expira_en` contra la fecha actual en las
    consultas, nunca con una restricción de unicidad permanente.
    """

    __tablename__ = "vendor_slug_historial"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    slug_anterior: Mapped[str] = mapped_column(String(63), nullable=False, index=True)
    expira_en: Mapped[datetime] = mapped_column(nullable=False)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    vendor: Mapped["Vendor"] = relationship(back_populates="slugs_anteriores")  # noqa: F821

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el slug anterior y el vendedor dueño.
        """
        return f"<VendorSlugHistorial {self.slug_anterior} vendor_id={self.vendor_id}>"
