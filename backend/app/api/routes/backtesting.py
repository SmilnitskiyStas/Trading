from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.candle_repository import CandleRepository
from app.repositories.exchange_repository import ExchangeRepository
from app.repositories.trading_pair_repository import TradingPairRepository
from app.schemas.backtesting import BacktestRequest, BacktestResponse
from app.services.backtesting.service import BacktestingService
from app.services.risk.service import RiskService
from app.services.strategies.service import StrategyService
from app.api.routes.strategy import get_strategy_service

router = APIRouter(prefix="/api/v1", tags=["backtesting"])


def get_backtesting_service(
    session: AsyncSession = Depends(get_db_session),
    strategy_service: StrategyService = Depends(get_strategy_service),
) -> BacktestingService:
    return BacktestingService(
        exchange_repository=ExchangeRepository(session),
        trading_pair_repository=TradingPairRepository(session),
        candle_repository=CandleRepository(session),
        risk_service=RiskService(strategy_service=strategy_service),
    )


@router.post("/backtesting/run", response_model=BacktestResponse)
async def run_backtest(
    payload: BacktestRequest,
    backtesting_service: BacktestingService = Depends(get_backtesting_service),
) -> BacktestResponse:
    return await backtesting_service.run_backtest(payload)
