"""Agregar tabla blog_posts

Revision ID: 526abf980a0e
Revises: b56293326046
Create Date: 2026-08-17 16:27:07.829653

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '526abf980a0e'
down_revision = 'b56293326046'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'blog_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('titulo', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=200), nullable=False),
        sa.Column('resumen', sa.String(length=300), nullable=True),
        sa.Column('contenido_markdown', sa.Text(), nullable=False),
        sa.Column('imagen_url', sa.String(length=500), nullable=True),
        sa.Column('estado', sa.Enum('BORRADOR', 'PUBLICADO', name='estado_blog_post'), nullable=False),
        sa.Column('publicado_en', sa.DateTime(), nullable=True),
        sa.Column('creado_en', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_blog_posts_slug'), 'blog_posts', ['slug'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_blog_posts_slug'), table_name='blog_posts')
    op.drop_table('blog_posts')
