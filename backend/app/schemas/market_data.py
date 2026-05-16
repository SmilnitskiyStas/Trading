from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MarketDataSyncRequest(BaseModel):
    exchange: str = Field(default="binance")
    symbol: str = Field(default="BTC/USDT")
    timeframe: str = Field(default="1h")
    limit: int = Field(default=200, ge=1, le=5000)


class MarketDataSyncResponse(BaseModel):
    exchange: str
    symbol: str
    timeframe: str
    fetched_count: int
    stored_count: int
    status: str


class CandleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trading_pair_id: int
    timeframe: str
    open_time: datetime
    close_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
