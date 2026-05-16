from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class TradingPair(TimestampMixin, Base):
    __tablename__ = "trading_pairs"
    __table_args__ = (
        UniqueConstraint("exchange_id", "symbol", name="uq_trading_pairs_exchange_symbol"),
        UniqueConstraint("exchange_id", "base_asset", "quote_asset", name="uq_trading_pairs_exchange_assets"),
        Index("ix_trading_pairs_exchange_id_is_active", "exchange_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    base_asset: Mapped[str] = mapped_column(String(20), nullable=False)
    quote_asset: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    exchange = relationship("Exchange", back_populates="trading_pairs")
    candles = relationship(
        "Candle",
        back_populates="trading_pair",
        cascade="all, delete-orphan",
    )

