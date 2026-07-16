"""add audit_logs table

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-07-16

Idempotent: skips table if already present (create_all / prior runs).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def _has(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if not _has("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=80), nullable=False),
            sa.Column("target_type", sa.String(length=40), nullable=True),
            sa.Column("target_id", sa.String(length=80), nullable=True),
            sa.Column("meta_json", sa.Text(), nullable=True),
            sa.Column("ip", sa.String(length=64), nullable=True),
        )
        op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
        op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
        op.create_index("ix_audit_logs_target_id", "audit_logs", ["target_id"])


def downgrade() -> None:
    if _has("audit_logs"):
        op.drop_index("ix_audit_logs_target_id", table_name="audit_logs")
        op.drop_index("ix_audit_logs_action", table_name="audit_logs")
        op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
        op.drop_table("audit_logs")
