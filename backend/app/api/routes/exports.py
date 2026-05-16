from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_market_data_service
from app.api.routes.indicators import get_indicator_service
from app.db.session import get_db_session
from app.schemas.ml import MLTarget
from app.services.exports.service import ExportService
from app.services.indicators.service import IndicatorService
from app.services.market_data.service import MarketDataService

router = APIRouter(prefix="/api/v1/exports", tags=["exports"])


def get_export_service(
    session: AsyncSession = Depends(get_db_session),
    market_data_service: MarketDataService = Depends(get_market_data_service),
    indicator_service: IndicatorService = Depends(get_indicator_service),
) -> ExportService:
    return ExportService(
        session=session,
        market_data_service=market_data_service,
        indicator_service=indicator_service,
    )


@router.get("/manifest")
async def export_manifest(
    export_service: ExportService = Depends(get_export_service),
) -> JSONResponse:
    return JSONResponse(await export_service.build_manifest())


@router.get("/candles.csv")
async def export_candles_csv(
    exchange: str = Query(...),
    symbol: str = Query(...),
    timeframe: str = Query(...),
    limit: int = Query(default=3000, ge=1, le=10000),
    export_service: ExportService = Depends(get_export_service),
) -> Response:
    filename, content = await export_service.export_candles_csv(exchange, symbol, timeframe, limit)
    return _csv_response(filename, content)


@router.get("/paper-trades.csv")
async def export_paper_trades_csv(
    account_name: str = Query(default="paper-main"),
    limit: int = Query(default=5000, ge=1, le=20000),
    export_service: ExportService = Depends(get_export_service),
) -> Response:
    filename, content = await export_service.export_paper_trades_csv(account_name, limit)
    return _csv_response(filename, content)


@router.get("/events.csv")
async def export_events_csv(
    limit: int = Query(default=5000, ge=1, le=20000),
    export_service: ExportService = Depends(get_export_service),
) -> Response:
    filename, content = await export_service.export_events_csv(limit)
    return _csv_response(filename, content)


@router.get("/daily-reports.csv")
async def export_daily_reports_csv(
    account_name: str | None = Query(default=None),
    limit: int = Query(default=365, ge=1, le=5000),
    export_service: ExportService = Depends(get_export_service),
) -> Response:
    filename, content = await export_service.export_daily_reports_csv(account_name, limit)
    return _csv_response(filename, content)


@router.get("/ml-dataset.csv")
async def export_ml_dataset_csv(
    exchange: str = Query(...),
    symbol: str = Query(...),
    timeframe: str = Query(...),
    limit: int = Query(default=3000, ge=100, le=10000),
    target: MLTarget = Query(default=MLTarget.FUTURE_EDGE_LONG),
    forecast_horizon_candles: int = Query(default=3, ge=1, le=24),
    min_edge_percent: float = Query(default=0.4, ge=0.05, le=5.0),
    export_service: ExportService = Depends(get_export_service),
) -> Response:
    filename, content = await export_service.export_ml_dataset_csv(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        target=target,
        forecast_horizon_candles=forecast_horizon_candles,
        min_edge_percent=min_edge_percent,
    )
    return _csv_response(filename, content)


def _csv_response(filename: str, content: str) -> Response:
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
