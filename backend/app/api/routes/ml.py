from fastapi import APIRouter, Depends, Query

from app.api.routes.indicators import get_indicator_service
from app.schemas.ml import (
    MLActiveModelResponse,
    MLModelDetailResponse,
    MLModelReviewRequest,
    MLModelSummary,
    MLPinModelRequest,
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


@router.get("/ml/model-detail", response_model=MLModelDetailResponse)
async def get_model_detail(
    model_id: str = Query(...),
    ml_service: MLService = Depends(get_ml_service),
) -> MLModelDetailResponse:
    return ml_service.get_model_detail(model_id=model_id)


@router.get("/ml/active-model", response_model=MLActiveModelResponse)
async def get_active_model(
    symbol: str = Query(...),
    timeframe: str = Query(...),
    ml_service: MLService = Depends(get_ml_service),
) -> MLActiveModelResponse:
    return ml_service.get_active_model(symbol=symbol, timeframe=timeframe)


@router.post("/ml/pin-model", response_model=MLActiveModelResponse)
async def pin_model(
    payload: MLPinModelRequest,
    ml_service: MLService = Depends(get_ml_service),
) -> MLActiveModelResponse:
    return ml_service.pin_model(payload)


@router.post("/ml/unpin-model", response_model=MLActiveModelResponse)
async def unpin_model(
    symbol: str = Query(...),
    timeframe: str = Query(...),
    ml_service: MLService = Depends(get_ml_service),
) -> MLActiveModelResponse:
    return ml_service.unpin_model(symbol=symbol, timeframe=timeframe)


@router.post("/ml/review-model", response_model=MLModelDetailResponse)
async def review_model(
    payload: MLModelReviewRequest,
    ml_service: MLService = Depends(get_ml_service),
) -> MLModelDetailResponse:
    return ml_service.review_model(payload)
