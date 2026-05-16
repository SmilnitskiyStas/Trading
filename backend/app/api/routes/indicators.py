from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_market_data_service
from app.schemas.indicators import IndicatorResponse
from app.services.indicators.service import IndicatorService
from app.services.market_data.service import MarketDataService

router = APIRouter(prefix="/api/v1", tags=["indicators"])


def get_indicator_service(
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> IndicatorService:
    return IndicatorService(market_data_service=market_data_service)


@router.get("/indicators", response_model=IndicatorResponse)
async def get_indicators(
    exchange: str = Query(..., description="Exchange slug, for example binance"),
    symbol: str = Query(..., description="Trading pair symbol, for example BTC/USDT"),
    timeframe: str = Query(..., description="Timeframe, for example 1h"),
    limit: int = Query(default=200, ge=30, le=1000),
    indicator_service: IndicatorService = Depends(get_indicator_service),
) -> IndicatorResponse:
    return await indicator_service.get_indicator_snapshot(
        exchange_slug=exchange,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
    )
