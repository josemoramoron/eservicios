"""Modelos de orden de compra: Order y OrderItem."""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.extensions import db


class EstadoOrder(str, enum.Enum):
    """Estado del ciclo de vida de una orden de compra."""

    PENDIENTE = "pendiente"
    PAGADO = "pagado"
    ENVIADO = "enviado"
    CANCELADO = "cancelado"


class Order(db.Model):
    """Orden de compra generada desde el carrito.

    Soporta checkout de invitado (no hay cuentas de cliente en el
    sitio): la orden se identifica por `email`, no por `user_id`.
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[EstadoOrder] = mapped_column(
        SqlEnum(EstadoOrder, name="estado_order"), default=EstadoOrder.PENDIENTE, nullable=False
    )
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    stripe_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el id y estado de la orden.
        """
        return f"<Order {self.id} {self.estado.value}>"


class OrderItem(db.Model):
    """Línea de detalle dentro de una `Order`."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    offering_id: Mapped[int] = mapped_column(ForeignKey("offerings.id"), nullable=False)
    cantidad: Mapped[int] = mapped_column(default=1, nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    offering: Mapped["Offering"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        """Representación legible para debugging.

        Returns:
            Cadena con el id de la línea y la cantidad.
        """
        return f"<OrderItem {self.id} x{self.cantidad}>"
