"""Agregar imagen_url a categories

Revision ID: b56293326046
Revises: fc1cd3469f2a
Create Date: 2026-08-02 20:37:51.864196

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b56293326046'
down_revision = 'fc1cd3469f2a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('categories', sa.Column('imagen_url', sa.String(length=500), nullable=True))


def downgrade():
    op.drop_column('categories', 'imagen_url')
