"""Agregar valor PLUS en mayuscula al enum plan_vendor

Revision ID: 8a56122a86a3
Revises: d7c18b4776c5
Create Date: 2026-08-30 19:08:07.057067

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a56122a86a3'
down_revision = 'd7c18b4776c5'
branch_labels = None
depends_on = None


def upgrade():
    # SqlEnum(PlanVendor, name="plan_vendor") en app/models/vendor.py no usa
    # values_callable, así que SQLAlchemy persiste por defecto el .name de
    # cada miembro del enum (mayúsculas: "FREE", "PLUS"), no su .value
    # (minúsculas: "free", "plus") — el tipo plan_vendor en Postgres ya
    # tenía la etiqueta 'FREE' (mayúscula) desde la migración original
    # (b15608102728). La migración anterior (9aad808618f8) agregó 'plus'
    # en minúscula por error, asumiendo que se usaba .value — ese valor
    # queda sin uso (Postgres no permite quitar valores de un enum), y acá
    # agregamos el que realmente hace falta: 'PLUS' en mayúscula.
    op.execute("ALTER TYPE plan_vendor ADD VALUE IF NOT EXISTS 'PLUS'")


def downgrade():
    # Postgres no permite quitar un valor de un tipo ENUM sin recrear el
    # tipo completo (y todas las columnas que lo usan) — igual que ya se
    # documentó en 9aad808618f8. Revertir esta migración no revierte el
    # ALTER TYPE; en la práctica es inofensivo dejar 'PLUS' en el tipo
    # aunque se haga rollback del resto del cambio.
    pass
