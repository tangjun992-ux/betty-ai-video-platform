"""add projects, payment_orders, gallery_likes business tables

Revision ID: f1a2b3c4d5e6
Revises: e1e9fe1d53fe
Create Date: 2026-07-11

Idempotent: skips tables already created by Base.metadata.create_all (dev), so it
is safe to run on both fresh DBs and existing ones. Brings the newer business
tables into the alembic track for production Postgres deployments.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e1e9fe1d53fe"
branch_labels = None
depends_on = None


def _has(table: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table)


def upgrade() -> None:
    if not _has("projects"):
        op.create_table(
            "projects",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("cover", sa.String(length=1000), nullable=True),
            sa.Column("items", sa.JSON(), nullable=False),
        )
        op.create_index("ix_projects_project_id", "projects", ["project_id"], unique=True)
        op.create_index("ix_projects_user_id", "projects", ["user_id"])

    if not _has("payment_orders"):
        op.create_table(
            "payment_orders",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("order_no", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("kind", sa.String(length=20), nullable=False),
            sa.Column("item_id", sa.String(length=60), nullable=False),
            sa.Column("cycle", sa.String(length=20), nullable=True),
            sa.Column("credits", sa.Integer(), nullable=False),
            sa.Column("amount_usd", sa.Float(), nullable=False),
            sa.Column("amount_cny", sa.Float(), nullable=False),
            sa.Column("label", sa.String(length=200), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("qr_content", sa.Text(), nullable=True),
            sa.Column("provider_txn_id", sa.String(length=128), nullable=True),
            sa.Column("granted", sa.Boolean(), nullable=False),
        )
        op.create_index("ix_payment_orders_order_no", "payment_orders", ["order_no"], unique=True)
        op.create_index("ix_payment_orders_user_id", "payment_orders", ["user_id"])

    if not _has("gallery_likes"):
        op.create_table(
            "gallery_likes",
            sa.Column("item_key", sa.Text(), primary_key=True),
            sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    for t in ("gallery_likes", "payment_orders", "projects"):
        if _has(t):
            op.drop_table(t)
