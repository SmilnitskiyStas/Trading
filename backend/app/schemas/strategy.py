from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.schemas.indicators import IndicatorSnapshot


class StrategySignal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class StrategyEvaluationRequest(BaseModel):
    exchange: str = Field(default="binance")
    symbol: str = Field(default="BTC/USDT")
    timeframe: str = Field(default="1h")
    limit: int = Field(default=250, ge=50, le=1000)
    strategy_name: str = Field(default=get_settings().strategy_default_name)


class StrategyEvaluationResponse(BaseModel):
    strategy_name: str
    exchange: str
    symbol: str
    timeframe: str
    signal: StrategySignal
    reasons: list[str]
    candle_count: int
    evaluated_at: datetime
    latest_close_price: Decimal
    latest_indicators: IndicatorSnapshot
