from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class PaperAccount(TimestampMixin, Base):
    __tablename__ = "paper_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    initial_balance: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    current_balance: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    trades = relationship("PaperTrade", back_populates="account", cascade="all, delete-orphan")

