from fastapi import APIRouter, Depends

from app.api.routes.strategy import get_strategy_service
from app.schemas.risk import RiskEvaluationRequest, RiskEvaluationResponse
from app.services.ml.service import MLService
from app.services.risk.service import RiskService
from app.services.strategies.service import StrategyService

router = APIRouter(prefix="/api/v1", tags=["risk"])


def get_risk_service(
    strategy_service: StrategyService = Depends(get_strategy_service),
) -> RiskService:
    return RiskService(
        strategy_service=strategy_service,
        ml_service=MLService(strategy_service.indicator_service),
    )


@router.post("/risk/evaluate", response_model=RiskEvaluationResponse)
async def evaluate_risk(
    payload: RiskEvaluationRequest,
    risk_service: RiskService = Depends(get_risk_service),
) -> RiskEvaluationResponse:
    return await risk_service.evaluate(payload)
