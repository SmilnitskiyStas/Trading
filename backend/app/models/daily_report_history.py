from datetime import date

from sqlalchemy import Date, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class DailyReportHistory(TimestampMixin, Base):
    __tablename__ = "daily_report_history"
    __table_args__ = (
        Index("ix_daily_report_history_report_date", "report_date"),
        Index("ix_daily_report_history_account_id_created_at", "account_id", "created_at"),
        Index("ix_daily_report_history_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("paper_accounts.id", ondelete="SET NULL"), nullable=True)
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)

    account = relationship("PaperAccount")
