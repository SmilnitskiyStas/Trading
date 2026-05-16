from fastapi import APIRouter, Depends, Query

from app.api.routes.indicators import get_indicator_service
from app.schemas.ml import (
    MLModelSummary,
    MLPredictRequest,
    MLPredictResponse,
    MLTrainRequest,
    MLTrainResponse,
    MLWalkForwardRequest,
    MLWalkForwardResponse,
)
from app.services.indicators.service import IndicatorService
from app.services.ml.service import MLService

router = APIRouter(prefix="/api/v1", tags=["ml"])


def get_ml_service(
    indicator_service: IndicatorService = Depends(get_indicator_service),
) -> MLService:
    return MLService(indicator_service=indicator_service)


@router.post("/ml/train", response_model=MLTrainResponse)
async def train_model(
    payload: MLTrainRequest,
    ml_service: MLService = Depends(get_ml_service),
) -> MLTrainResponse:
    return await ml_service.train(payload)


@router.post("/ml/walk-forward", response_model=MLWalkForwardResponse)
async def walk_forward_model(
    payload: MLWalkForwardRequest,
    ml_service: MLService = Depends(get_ml_service),
) -> MLWalkForwardResponse:
    return await ml_service.walk_forward(payload)


@router.post("/ml/predict", response_model=MLPredictResponse)
async def predict_model(
    payload: MLPredictRequest,
    ml_service: MLService = Depends(get_ml_service),
) -> MLPredictResponse:
    return await ml_service.predict(payload)


@router.get("/ml/models", response_model=list[MLModelSummary])
async def list_models(
    symbol: str | None = Query(default=None),
    timeframe: str | None = Query(default=None),
    ml_service: MLService = Depends(get_ml_service),
) -> list[MLModelSummary]:
    return ml_service.list_models(symbol=symbol, timeframe=timeframe)
