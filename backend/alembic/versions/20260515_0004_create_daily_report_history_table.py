"""create daily report history table

Revision ID: 20260515_0004
Revises: 20260515_0003
Create Date: 2026-05-15 22:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260515_0004"
down_revision: str | None = "20260515_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_report_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("account_name", sa.String(length=100), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["paper_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_daily_report_history_report_date", "daily_report_history", ["report_date"], unique=False)
    op.create_index(
        "ix_daily_report_history_account_id_created_at",
        "daily_report_history",
        ["account_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_daily_report_history_status_created_at",
        "daily_report_history",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_daily_report_history_status_created_at", table_name="daily_report_history")
    op.drop_index("ix_daily_report_history_account_id_created_at", table_name="daily_report_history")
    op.drop_index("ix_daily_report_history_report_date", table_name="daily_report_history")
    op.drop_table("daily_report_history")
