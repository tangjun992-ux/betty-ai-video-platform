"""add timeline_projects + gallery_views tables

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-07-12

Idempotent: skips tables already present (CREATE TABLE IF NOT EXISTS style via
inspector), safe on fresh DBs and ones bootstrapped via Base.metadata.create_all.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def _has(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if not _has("timeline_projects"):
        op.create_table(
            "timeline_projects",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("clips", sa.JSON(), nullable=False),
        )
        op.create_index("ix_timeline_projects_project_id", "timeline_projects", ["project_id"], unique=True)
        op.create_index("ix_timeline_projects_user_id", "timeline_projects", ["user_id"])

    if not _has("gallery_views"):
        op.create_table(
            "gallery_views",
            sa.Column("item_key", sa.Text(), primary_key=True),
            sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    for t in ("gallery_views", "timeline_projects"):
        if _has(t):
            op.drop_table(t)
