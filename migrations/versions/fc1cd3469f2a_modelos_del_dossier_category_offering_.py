"""Modelos del dossier: Category, Offering, Order, OrderItem, AdminUser, Lead, Testimonial

Generado con `flask db migrate` contra una BD vacía (SQLite temporal,
solo para autogenerar) y revisado a mano para Postgres: se reemplazó
`batch_alter_table` (necesario solo en SQLite) por `create_index`/
`drop_index` directos, y se limpió el `server_default` de las columnas
`created_at`.

Revision ID: fc1cd3469f2a
Revises:
Create Date: 2026-07-31 10:59:33.767375

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fc1cd3469f2a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'admin_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('rol', sa.Enum('OWNER', 'STAFF', name='rol_admin'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_admin_users_email'), 'admin_users', ['email'], unique=True)

    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=120), nullable=False),
        sa.Column('slug', sa.String(length=120), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('orden', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_categories_slug'), 'categories', ['slug'], unique=True)

    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('estado', sa.Enum('PENDIENTE', 'PAGADO', 'ENVIADO', 'CANCELADO', name='estado_order'), nullable=False),
        sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('stripe_payment_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'offerings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=150), nullable=False),
        sa.Column('slug', sa.String(length=150), nullable=False),
        sa.Column('tipo', sa.Enum('PRODUCTO', 'SERVICIO', 'CURSO', 'CONSULTORIA', name='tipo_offering'), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=False),
        sa.Column('imagen_url', sa.String(length=500), nullable=True),
        sa.Column('precio', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('vendible', sa.Boolean(), nullable=False),
        sa.Column('stock', sa.Integer(), nullable=True),
        sa.Column('destacado', sa.Boolean(), nullable=False),
        sa.Column('activo', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_offerings_slug'), 'offerings', ['slug'], unique=True)

    op.create_table(
        'leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=150), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('telefono', sa.String(length=50), nullable=True),
        sa.Column('offering_id', sa.Integer(), nullable=True),
        sa.Column('mensaje', sa.Text(), nullable=False),
        sa.Column('atendido', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['offering_id'], ['offerings.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('offering_id', sa.Integer(), nullable=False),
        sa.Column('cantidad', sa.Integer(), nullable=False),
        sa.Column('precio_unitario', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['offering_id'], ['offerings.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'testimonials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cliente', sa.String(length=150), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('offering_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['offering_id'], ['offerings.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('testimonials')
    op.drop_table('order_items')
    op.drop_table('leads')
    op.drop_index(op.f('ix_offerings_slug'), table_name='offerings')
    op.drop_table('offerings')
    op.drop_table('orders')
    op.drop_index(op.f('ix_categories_slug'), table_name='categories')
    op.drop_table('categories')
    op.drop_index(op.f('ix_admin_users_email'), table_name='admin_users')
    op.drop_table('admin_users')
