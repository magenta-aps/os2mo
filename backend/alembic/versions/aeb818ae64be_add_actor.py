# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
"""Add actor table."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "aeb818ae64be"
down_revision: str | Sequence[str] | None = "b1533c198dab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "actor",
        sa.Column(
            "actor",
            sa.Uuid,
            primary_key=True,
        ),
        sa.Column("name", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("actor")
