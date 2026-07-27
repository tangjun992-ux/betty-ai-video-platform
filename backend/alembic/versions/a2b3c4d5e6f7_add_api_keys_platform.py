"""add api_keys_platform table (developer API keys)

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-11

Idempotent (inspector-guarded): safe on DBs already created via create_all.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def _has(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if _has("api_keys_platform"):
        return
    op.create_table(
        "api_keys_platform",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("key_id", sa.String(length=40), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_api_keys_platform_key_id", "api_keys_platform", ["key_id"], unique=True)
    op.create_index("ix_api_keys_platform_key_hash", "api_keys_platform", ["key_hash"])
    op.create_index("ix_api_keys_platform_user_id", "api_keys_platform", ["user_id"])


def downgrade() -> None:
    if _has("api_keys_platform"):
        op.drop_table("api_keys_platform")
