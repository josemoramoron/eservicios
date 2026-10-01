"""Consolidar columnas de video en video_plataforma/video_valor (8 plataformas)

Revision ID: 6d9a798e63df
Revises: a389235e6f9a
Create Date: 2026-10-01 00:00:00.000000

Reemplaza el esquema de "una columna (o par de columnas) por cada
plataforma de video" por dos columnas genéricas — video_plataforma
(clave corta: youtube/tiktok/vimeo/twitch_video/twitch_clip/facebook/
threads/instagram/x) y video_valor (ID o URL completa, según la
plataforma) — tanto en vendor_products (video del producto, exclusivo
de e-link Plus) como en vendors (video-tráiler del perfil, gratis para
cualquier plan). Ver app/services/video_service.py para el detalle de
qué guarda cada plataforma en video_valor.

Las columnas viejas (youtube_video_id, tiktok_video_url en
vendor_products; youtube_trailer_video_id, tiktok_trailer_video_url en
vendors) NO se eliminan — se dejan como respaldo histórico de datos de
producción ya existentes — simplemente dejan de estar mapeadas en los
modelos de SQLAlchemy. Esta migración agrega las columnas nuevas y
hace un backfill desde las viejas.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d9a798e63df'
down_revision = 'a389235e6f9a'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('vendor_products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('video_plataforma', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('video_valor', sa.String(length=300), nullable=True))

    with op.batch_alter_table('vendors', schema=None) as batch_op:
        batch_op.add_column(sa.Column('video_trailer_plataforma', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('video_trailer_valor', sa.String(length=300), nullable=True))

    # Backfill: cada producto/vendor tenía a lo sumo una de las dos
    # columnas viejas con valor (youtube XOR tiktok), así que el orden
    # de estos dos UPDATE por tabla no importa.
    op.execute(
        "UPDATE vendor_products SET video_plataforma = 'youtube', video_valor = youtube_video_id "
        "WHERE youtube_video_id IS NOT NULL"
    )
    op.execute(
        "UPDATE vendor_products SET video_plataforma = 'tiktok', video_valor = tiktok_video_url "
        "WHERE tiktok_video_url IS NOT NULL"
    )
    op.execute(
        "UPDATE vendors SET video_trailer_plataforma = 'youtube', video_trailer_valor = youtube_trailer_video_id "
        "WHERE youtube_trailer_video_id IS NOT NULL"
    )
    op.execute(
        "UPDATE vendors SET video_trailer_plataforma = 'tiktok', video_trailer_valor = tiktok_trailer_video_url "
        "WHERE tiktok_trailer_video_url IS NOT NULL"
    )


def downgrade():
    with op.batch_alter_table('vendors', schema=None) as batch_op:
        batch_op.drop_column('video_trailer_valor')
        batch_op.drop_column('video_trailer_plataforma')

    with op.batch_alter_table('vendor_products', schema=None) as batch_op:
        batch_op.drop_column('video_valor')
        batch_op.drop_column('video_plataforma')
