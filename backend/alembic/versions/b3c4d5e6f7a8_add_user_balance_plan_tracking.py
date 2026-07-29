"""add user_balance plan tracking (current_plan_id / plan_started_at / plan_cycle)

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-07-16

Idempotent (inspector-guarded): safe on DBs already created via create_all and on
DBs that predate these columns. Persists the user's active subscription plan so
mid-cycle plan changes can be prorated against the days remaining in the cycle.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None

_TABLE = "user_balance"
_COLUMNS = {
    "current_plan_id": sa.Column("current_plan_id", sa.String(length=60), nullable=True),
    "plan_started_at": sa.Column("plan_started_at", sa.DateTime(timezone=True), nullable=True),
    "plan_cycle": sa.Column("plan_cycle", sa.String(length=20), nullable=True),
}


def _existing_columns(table: str) -> set:
    insp = sa.inspect(op.get_bind())
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table(_TABLE):
        return
    existing = _existing_columns(_TABLE)
    for name, column in _COLUMNS.items():
        if name not in existing:
            op.add_column(_TABLE, column)


def downgrade() -> None:
    existing = _existing_columns(_TABLE)
    for name in _COLUMNS:
        if name in existing:
            op.drop_column(_TABLE, name)
