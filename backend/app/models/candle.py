from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint(
            "trading_pair_id",
            "timeframe",
            "open_time",
            name="uq_candles_pair_timeframe_open_time",
        ),
        Index("ix_candles_pair_timeframe_open_time", "trading_pair_id", "timeframe", "open_time"),
        Index("ix_candles_timeframe_open_time", "timeframe", "open_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trading_pair_id: Mapped[int] = mapped_column(
        ForeignKey("trading_pairs.id", ondelete="CASCADE"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    high_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    low_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(28, 8), nullable=False)

    trading_pair = relationship("TradingPair", back_populates="candles")

