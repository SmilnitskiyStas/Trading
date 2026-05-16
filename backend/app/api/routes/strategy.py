from fastapi import APIRouter, Depends

from app.api.routes.indicators import get_indicator_service
from app.schemas.strategy import StrategyEvaluationRequest, StrategyEvaluationResponse
from app.services.indicators.service import IndicatorService
from app.services.strategies.service import StrategyService

router = APIRouter(prefix="/api/v1", tags=["strategy"])


def get_strategy_service(
    indicator_service: IndicatorService = Depends(get_indicator_service),
) -> StrategyService:
    return StrategyService(indicator_service=indicator_service)


@router.post("/strategy/evaluate", response_model=StrategyEvaluationResponse)
async def evaluate_strategy(
    payload: StrategyEvaluationRequest,
    strategy_service: StrategyService = Depends(get_strategy_service),
) -> StrategyEvaluationResponse:
    return await strategy_service.evaluate(payload)
