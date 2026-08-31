"""Modelo de producto subido por un vendedor a su propia tienda."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.extensions import db


class VendorProduct(db.Model):
    """Producto que un vendedor sube a su propia tienda (`Vendor`).

    Sin moderación por ahora: se publica de inmediato al crearse
    (`activo=True` por defecto). El precio es un número simple, sin
    moneda propia — toda la tienda cotiza en la moneda elegida por el
    vendedor (`Vendor.moneda`, roadmap Fase 2 punto 20, gratis para
    cualquier plan), no hay selector de moneda por producto. Ver
    `app/services/monedas_service.formatear_precio` para el formato de
    despliegue — no hay conversión automática entre monedas.
    """

    __tablename__ = "vendor_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    foto_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Badge opcional ("Más vendido", "Oferta", "Nuevo"), función de e-link
    # Plus (roadmap, Fase 2, punto 14) — ver
    # app/services/badges_producto_service.py para las claves válidas.
    # None = sin badge. Se guarda aunque el plan no esté vigente en este
    # momento, igual que color_acento/plantilla en Vendor; la aplicación
    # real siempre se resuelve en tiempo de render (ver
    # vendor_service.resolver_badge_producto).
    badge: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Estado manual de stock ("pocas_unidades" / "agotado"), función de
    # e-link Plus (roadmap, Fase 2, punto 17) — ver
    # app/services/estados_stock_service.py para las claves válidas. None
    # = "Normal" (no se muestra ningún indicador). Igual que badge, se
    # guarda aunque el plan no esté vigente en este momento; la
    # aplicación real siempre se resuelve en tiempo de render (ver
    # vendor_service.resolver_estado_stock_producto). Cuando vale
    # "agotado", la tienda pública ofrece el mini-formulario "avísame
    # cuando vuelva" (ver VendorProductAviso).
    estado_stock: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Categoría propia del vendedor (una por producto), función de e-link
    # Plus (roadmap, Fase 2, punto 18) — ver vendor_service para el CRUD
    # de VendorCategoria. Nullable: un producto sin categorizar sigue
    # siendo válido y se muestra igual en la tienda pública (fuera del
    # filtro de categorías). Al borrar la categoría, el servicio pone
    # este campo en None a mano en cada producto afectado antes de
    # borrar la fila de VendorCategoria (mismo criterio de limpieza
    # manual que vendor_admin_service.eliminar_vendor_permanente usa
    # para VendorEvento/VendorReporte, en vez de depender de un
    # ON DELETE a nivel de base de datos).
    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("vendor_categorias.id"), nullable=True, index=True
    )
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    vendor: Mapped["Vendor"] = relationship(back_populates="productos")  # noqa: F821
    fotos: Mapped[list["VendorProductFoto"]] = relationship(  # noqa: F821
        back_populates="producto", cascade="all, delete-orphan", order_by="VendorProductFoto.orden"
    )
    # A diferencia de `fotos`, sí usa cascade="all, delete-orphan": un
    # aviso de "avísame cuando vuelva" no tiene sentido fuera de su
    # producto (no lo consulta nadie más que el propio vendedor desde
    # /vendedor/avisos), así que se borra solo si se borra el producto —
    # mismo criterio que fotos, sin necesidad de limpieza manual.
    avisos: Mapped[list["VendorProductAviso"]] = relationship(  # noqa: F821
        back_populates="producto", cascade="all, delete-orphan", order_by="VendorProductAviso.creado_en.desc()"
    )
    categoria: Mapped["VendorCategoria | None"] = relationship(back_populates="productos")  # noqa: F821

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el id y el título del producto.
        """
        return f"<VendorProduct {self.id} {self.titulo}>"
