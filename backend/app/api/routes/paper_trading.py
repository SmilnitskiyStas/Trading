from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.strategy import get_strategy_service
from app.db.session import get_db_session
from app.schemas.paper_trading import (
    PaperAccountRead,
    PaperTradingPerformanceByDayRead,
    PaperTradingPerformanceBySymbolRead,
    PaperTradingPerformanceRead,
    PaperTradingTestStatusRead,
    PaperTradeRead,
    PaperTradingCycleRequest,
    PaperTradingCycleResponse,
)
from app.services.ml.service import MLService
from app.services.execution.paper_trading import PaperTradingService
from app.services.risk.service import RiskService
from app.services.strategies.service import StrategyService

router = APIRouter(prefix="/api/v1/paper-trading", tags=["paper-trading"])


def get_paper_trading_service(
    session: AsyncSession = Depends(get_db_session),
    strategy_service: StrategyService = Depends(get_strategy_service),
) -> PaperTradingService:
    return PaperTradingService(
        session=session,
        risk_service=RiskService(
            strategy_service=strategy_service,
            ml_service=MLService(strategy_service.indicator_service),
        ),
    )


@router.post("/cycle", response_model=PaperTradingCycleResponse)
async def run_paper_trading_cycle(
    payload: PaperTradingCycleRequest,
    paper_trading_service: PaperTradingService = Depends(get_paper_trading_service),
) -> PaperTradingCycleResponse:
    return await paper_trading_service.run_cycle(payload)


@router.get("/account", response_model=PaperAccountRead)
async def get_paper_account(
    account_name: str = Query(default="paper-main"),
    paper_trading_service: PaperTradingService = Depends(get_paper_trading_service),
) -> PaperAccountRead:
    return await paper_trading_service.get_account(account_name)


@router.get("/trades", response_model=list[PaperTradeRead])
async def list_paper_trades(
    account_name: str = Query(default="paper-main"),
    limit: int = Query(default=100, ge=1, le=500),
    paper_trading_service: PaperTradingService = Depends(get_paper_trading_service),
) -> list[PaperTradeRead]:
    return await paper_trading_service.list_trades(account_name=account_name, limit=limit)


@router.get("/performance", response_model=PaperTradingPerformanceRead)
async def get_paper_trading_performance(
    account_name: str = Query(default="paper-main"),
    paper_trading_service: PaperTradingService = Depends(get_paper_trading_service),
) -> PaperTradingPerformanceRead:
    return await paper_trading_service.get_performance(account_name=account_name)


@router.get("/performance/by-day", response_model=list[PaperTradingPerformanceByDayRead])
async def get_paper_trading_performance_by_day(
    account_name: str = Query(default="paper-main"),
    paper_trading_service: PaperTradingService = Depends(get_paper_trading_service),
) -> list[PaperTradingPerformanceByDayRead]:
    return await paper_trading_service.get_performance_by_day(account_name=account_name)


@router.get("/performance/by-symbol", response_model=list[PaperTradingPerformanceBySymbolRead])
async def get_paper_trading_performance_by_symbol(
    account_name: str = Query(default="paper-main"),
    paper_trading_service: PaperTradingService = Depends(get_paper_trading_service),
) -> list[PaperTradingPerformanceBySymbolRead]:
    return await paper_trading_service.get_performance_by_symbol(account_name=account_name)


@router.get("/test-status", response_model=PaperTradingTestStatusRead)
async def get_paper_trading_test_status(
    account_name: str = Query(default="paper-main"),
    paper_trading_service: PaperTradingService = Depends(get_paper_trading_service),
) -> PaperTradingTestStatusRead:
    return await paper_trading_service.get_test_status(account_name=account_name)
