"""create system events table

Revision ID: 20260515_0003
Revises: 20260515_0002
Create Date: 2026-05-15 01:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260515_0003"
down_revision = "20260515_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("paper_trade_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["paper_accounts.id"], name=op.f("fk_system_events_account_id_paper_accounts"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["paper_trade_id"], ["paper_trades.id"], name=op.f("fk_system_events_paper_trade_id_paper_trades"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_system_events")),
    )
    op.create_index("ix_system_events_account_id_created_at", "system_events", ["account_id", "created_at"], unique=False)
    op.create_index("ix_system_events_event_type_created_at", "system_events", ["event_type", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_system_events_event_type_created_at", table_name="system_events")
    op.drop_index("ix_system_events_account_id_created_at", table_name="system_events")
    op.drop_table("system_events")
