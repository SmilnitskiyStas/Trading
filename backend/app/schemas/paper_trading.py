from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.config import get_settings

class PaperTradingCycleRequest(BaseModel):
    account_name: str = Field(default="paper-main")
    exchange: str = Field(default="binance")
    symbol: str = Field(default="BTC/USDT")
    timeframe: str = Field(default="1h")
    limit: int = Field(default=250, ge=50, le=1000)
    strategy_name: str = Field(default=get_settings().strategy_default_name)


class PaperAccountRead(BaseModel):
    id: int
    name: str
    initial_balance: Decimal
    current_balance: Decimal
    is_active: bool

    class Config:
        from_attributes = True


class PaperTradeRead(BaseModel):
    id: int
    account_id: int
    trading_pair_id: int
    strategy_name: str
    timeframe: str
    status: str
    side: str
    entry_price: Decimal
    exit_price: Decimal | None
    stop_loss_price: Decimal
    take_profit_price: Decimal
    position_size: Decimal
    fees_paid: Decimal
    realized_pnl: Decimal
    exit_reason: str | None
    opened_at: datetime
    closed_at: datetime | None

    class Config:
        from_attributes = True


class PaperTradingPerformanceRead(BaseModel):
    account_name: str
    initial_balance: Decimal
    current_balance: Decimal
    realized_pnl: Decimal
    realized_return_percent: Decimal
    total_trades: int
    open_trades: int
    closed_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_percent: Decimal
    average_win: Decimal
    average_loss: Decimal
    profit_factor: Decimal
    current_drawdown_percent: Decimal
    max_drawdown_percent: Decimal


class PaperTradingPerformanceByDayRead(BaseModel):
    trading_day: date
    closed_trades: int
    winning_trades: int
    losing_trades: int
    realized_pnl: Decimal
    win_rate_percent: Decimal


class PaperTradingPerformanceBySymbolRead(BaseModel):
    symbol: str
    closed_trades: int
    winning_trades: int
    losing_trades: int
    realized_pnl: Decimal
    win_rate_percent: Decimal
    profit_factor: Decimal


class PaperTradingCycleResponse(BaseModel):
    account: PaperAccountRead
    action: str
    reasons: list[str]
    trade: PaperTradeRead | None


class PaperTradingTestStatusRead(BaseModel):
    account_name: str
    phase: str
    pnl_status: str
    ready_for_evaluation: bool
    current_balance: Decimal
    realized_pnl: Decimal
    realized_return_percent: Decimal
    closed_trades: int
    open_trades: int
    days_with_closed_trades: int
    last_closed_trade_at: datetime | None
    last_closed_trade_pnl: Decimal | None
    summary: str
