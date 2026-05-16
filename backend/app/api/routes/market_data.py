from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_market_data_service
from app.schemas.market_data import CandleRead, MarketDataSyncRequest, MarketDataSyncResponse
from app.services.market_data.service import MarketDataService

router = APIRouter(prefix="/api/v1", tags=["market-data"])


@router.get("/candles", response_model=list[CandleRead])
async def list_candles(
    exchange: str = Query(..., description="Exchange slug, for example binance"),
    symbol: str = Query(..., description="Trading pair symbol, for example BTC/USDT"),
    timeframe: str = Query(..., description="Timeframe, for example 1h"),
    limit: int = Query(default=200, ge=1, le=5000),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> list[CandleRead]:
    candles = await market_data_service.list_candles(
        exchange_slug=exchange,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
    )
    return [CandleRead.model_validate(candle) for candle in candles]


@router.post(
    "/market-data/sync",
    response_model=MarketDataSyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sync_market_data(
    payload: MarketDataSyncRequest,
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> MarketDataSyncResponse:
    return await market_data_service.sync_ohlcv(payload)
