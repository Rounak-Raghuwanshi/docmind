"""Flag the public demo workspace (and allow at most one).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workspaces", sa.Column("is_demo", sa.Boolean, server_default=sa.false(), nullable=False)
    )
    op.create_index(
        "uq_workspaces_single_demo",
        "workspaces",
        ["is_demo"],
        unique=True,
        postgresql_where=sa.text("is_demo"),
    )


def downgrade() -> None:
    op.drop_index("uq_workspaces_single_demo", table_name="workspaces")
    op.drop_column("workspaces", "is_demo")
