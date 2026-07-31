"""Modelo de usuario administrador (acceso al panel /admin)."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class RolAdmin(str, enum.Enum):
    """Rol del usuario administrador."""

    OWNER = "owner"
    STAFF = "staff"


class AdminUser(db.Model):
    """Usuario con acceso al panel de administración (`/admin`).

    Separado por completo de los clientes: el sitio no tiene cuentas
    de cliente, el checkout siempre es de invitado.
    """

    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolAdmin] = mapped_column(
        SqlEnum(RolAdmin, name="rol_admin"), default=RolAdmin.STAFF, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

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
            Cadena con el email del administrador.
        """
        return f"<AdminUser {self.email}>"
