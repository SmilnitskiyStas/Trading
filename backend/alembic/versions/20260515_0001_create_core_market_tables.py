"""create core market tables

Revision ID: 20260515_0001
Revises:
Create Date: 2026-05-15 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260515_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exchanges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exchanges")),
        sa.UniqueConstraint("name", name=op.f("uq_exchanges_name")),
        sa.UniqueConstraint("slug", name=op.f("uq_exchanges_slug")),
    )

    op.create_table(
        "trading_pairs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("base_asset", sa.String(length=20), nullable=False),
        sa.Column("quote_asset", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["exchange_id"],
            ["exchanges.id"],
            name=op.f("fk_trading_pairs_exchange_id_exchanges"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trading_pairs")),
        sa.UniqueConstraint("exchange_id", "base_asset", "quote_asset", name="uq_trading_pairs_exchange_assets"),
        sa.UniqueConstraint("exchange_id", "symbol", name="uq_trading_pairs_exchange_symbol"),
    )
    op.create_index(
        "ix_trading_pairs_exchange_id_is_active",
        "trading_pairs",
        ["exchange_id", "is_active"],
        unique=False,
    )

    op.create_table(
        "candles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trading_pair_id", sa.Integer(), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("high_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("low_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("close_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("volume", sa.Numeric(precision=28, scale=8), nullable=False),
        sa.ForeignKeyConstraint(
            ["trading_pair_id"],
            ["trading_pairs.id"],
            name=op.f("fk_candles_trading_pair_id_trading_pairs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candles")),
        sa.UniqueConstraint(
            "trading_pair_id",
            "timeframe",
            "open_time",
            name="uq_candles_pair_timeframe_open_time",
        ),
    )
    op.create_index(
        "ix_candles_pair_timeframe_open_time",
        "candles",
        ["trading_pair_id", "timeframe", "open_time"],
        unique=False,
    )
    op.create_index(
        "ix_candles_timeframe_open_time",
        "candles",
        ["timeframe", "open_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_candles_timeframe_open_time", table_name="candles")
    op.drop_index("ix_candles_pair_timeframe_open_time", table_name="candles")
    op.drop_table("candles")
    op.drop_index("ix_trading_pairs_exchange_id_is_active", table_name="trading_pairs")
    op.drop_table("trading_pairs")
    op.drop_table("exchanges")
