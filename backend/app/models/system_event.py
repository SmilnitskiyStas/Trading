from sqlalchemy import ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class SystemEvent(TimestampMixin, Base):
    __tablename__ = "system_events"
    __table_args__ = (
        Index("ix_system_events_event_type_created_at", "event_type", "created_at"),
        Index("ix_system_events_account_id_created_at", "account_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("paper_accounts.id", ondelete="SET NULL"), nullable=True)
    paper_trade_id: Mapped[int | None] = mapped_column(ForeignKey("paper_trades.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    account = relationship("PaperAccount")
    paper_trade = relationship("PaperTrade")
