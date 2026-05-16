from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.config import get_settings

class BacktestRequest(BaseModel):
    exchange: str = Field(default="binance")
    symbol: str = Field(default="BTC/USDT")
    timeframe: str = Field(default="1h")
    limit: int = Field(default=500, ge=100, le=5000)
    strategy_name: str = Field(default=get_settings().strategy_default_name)
    initial_balance: Decimal = Field(default=Decimal("1000"))


class BacktestTrade(BaseModel):
    opened_at: datetime
    closed_at: datetime
    entry_price: Decimal
    exit_price: Decimal
    stop_loss_price: Decimal
    take_profit_price: Decimal
    position_size: Decimal
    fees_paid: Decimal
    pnl: Decimal
    pnl_percent: Decimal
    exit_reason: str


class BacktestMetrics(BaseModel):
    total_return_percent: Decimal
    ending_balance: Decimal
    max_drawdown_percent: Decimal
    win_rate_percent: Decimal
    profit_factor: Decimal
    sharpe_ratio: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int


class BacktestResponse(BaseModel):
    exchange: str
    symbol: str
    timeframe: str
    strategy_name: str
    initial_balance: Decimal
    metrics: BacktestMetrics
    trades: list[BacktestTrade]
