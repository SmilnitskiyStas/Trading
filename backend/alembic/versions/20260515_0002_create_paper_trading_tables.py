"""create paper trading tables

Revision ID: 20260515_0002
Revises: 20260515_0001
Create Date: 2026-05-15 00:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260515_0002"
down_revision = "20260515_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("initial_balance", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("current_balance", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paper_accounts")),
        sa.UniqueConstraint("name", name=op.f("uq_paper_accounts_name")),
    )
    op.create_table(
        "paper_trades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("trading_pair_id", sa.Integer(), nullable=False),
        sa.Column("strategy_name", sa.String(length=100), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("entry_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("exit_price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("stop_loss_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("take_profit_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("position_size", sa.Numeric(precision=28, scale=8), nullable=False),
        sa.Column("fees_paid", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("exit_reason", sa.String(length=50), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["paper_accounts.id"], name=op.f("fk_paper_trades_account_id_paper_accounts"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trading_pair_id"], ["trading_pairs.id"], name=op.f("fk_paper_trades_trading_pair_id_trading_pairs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paper_trades")),
    )
    op.create_index("ix_paper_trades_account_id_status", "paper_trades", ["account_id", "status"], unique=False)
    op.create_index("ix_paper_trades_trading_pair_id_status", "paper_trades", ["trading_pair_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_paper_trades_trading_pair_id_status", table_name="paper_trades")
    op.drop_index("ix_paper_trades_account_id_status", table_name="paper_trades")
    op.drop_table("paper_trades")
    op.drop_table("paper_accounts")
