from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class IndicatorSnapshot(BaseModel):
    open_time: datetime
    close_time: datetime
    close_price: Decimal
    ema_fast: float | None
    ema_slow: float | None
    ema_trend: float | None
    ema_by_period: dict[int, float | None] | None = None
    rsi: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    atr: float | None


class IndicatorResponse(BaseModel):
    exchange: str
    symbol: str
    timeframe: str
    candle_count: int
    indicators: list[IndicatorSnapshot]
