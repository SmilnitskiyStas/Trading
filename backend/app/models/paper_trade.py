from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class PaperTrade(TimestampMixin, Base):
    __tablename__ = "paper_trades"
    __table_args__ = (
        Index("ix_paper_trades_account_id_status", "account_id", "status"),
        Index("ix_paper_trades_trading_pair_id_status", "trading_pair_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("paper_accounts.id", ondelete="CASCADE"), nullable=False)
    trading_pair_id: Mapped[int] = mapped_column(ForeignKey("trading_pairs.id", ondelete="CASCADE"), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    stop_loss_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    take_profit_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    position_size: Mapped[Decimal] = mapped_column(Numeric(28, 8), nullable=False)
    fees_paid: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    exit_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    account = relationship("PaperAccount", back_populates="trades")
    trading_pair = relationship("TradingPair")
