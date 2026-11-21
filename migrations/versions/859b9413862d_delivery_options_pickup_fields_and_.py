"""delivery options, pickup fields and order snapshots

Revision ID: 859b9413862d
Revises: 3998f62a7695
Create Date: 2026-11-21 10:59:32.186148
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '859b9413862d'
down_revision = '3998f62a7695'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'order_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('html_path', sa.String(length=255), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('order_snapshots', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_order_snapshots_order_id'), ['order_id'], unique=True)

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pickup_location', sa.String(length=120), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('pickup_time', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('pickup_time_confirmed_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('pickup_location_set_at', sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('supports_pickup', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column('pickup_location', sa.String(length=120), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('supports_express', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column('free_shipping', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(
            sa.Column('shipping_fee', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0')
        )

    # 历史数据回填：旧"面交"并入"自提"；商品原有 location 作为默认自提点
    op.execute("UPDATE orders SET delivery_type = '自提' WHERE delivery_type = '面交'")
    op.execute("UPDATE products SET pickup_location = location WHERE pickup_location = '' AND location <> ''")
    op.execute(
        "UPDATE orders SET pickup_location = ("
        " SELECT p.pickup_location FROM order_items oi JOIN products p ON p.id = oi.product_id"
        " WHERE oi.order_id = orders.id AND p.pickup_location <> '' LIMIT 1"
        ") WHERE delivery_type = '自提' AND pickup_location = ''"
    )


def downgrade() -> None:
    op.execute("UPDATE orders SET delivery_type = '面交' WHERE delivery_type = '自提'")
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('shipping_fee')
        batch_op.drop_column('free_shipping')
        batch_op.drop_column('supports_express')
        batch_op.drop_column('pickup_location')
        batch_op.drop_column('supports_pickup')

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('pickup_location_set_at')
        batch_op.drop_column('pickup_time_confirmed_at')
        batch_op.drop_column('pickup_time')
        batch_op.drop_column('pickup_location')

    with op.batch_alter_table('order_snapshots', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_order_snapshots_order_id'))

    op.drop_table('order_snapshots')
