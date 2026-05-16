from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class MLTarget(str, Enum):
    NEXT_CLOSE_UP = "next_close_up"
    FUTURE_EDGE_LONG = "future_edge_long"


class MLAdvisorySignal(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    HOLD = "HOLD"


class MLDatasetSplitSummary(BaseModel):
    train_rows: int
    validation_rows: int
    test_rows: int


class MLMetricsSummary(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    positive_rate: float
    roc_auc: float | None = None


class MLTrainRequest(BaseModel):
    exchange: str = Field(default="binance")
    symbol: str = Field(default="BTC/USDT")
    timeframe: str = Field(default="1h")
    limit: int = Field(default=1000, ge=250, le=5000)
    target: MLTarget = Field(default=MLTarget.FUTURE_EDGE_LONG)
    forecast_horizon_candles: int = Field(default=3, ge=1, le=24)
    min_edge_percent: float = Field(default=0.4, ge=0.05, le=5.0)
    min_precision: float | None = Field(default=None, ge=0.05, le=0.99)
    min_positive_predictions: int | None = Field(default=None, ge=1, le=1000)
    confidence_threshold: float | None = Field(default=None, ge=0.5, le=0.99)


class MLTrainResponse(BaseModel):
    model_id: str
    exchange: str
    symbol: str
    timeframe: str
    target: MLTarget
    forecast_horizon_candles: int
    min_edge_percent: float
    min_precision: float
    min_positive_predictions: int
    algorithm: str
    trained_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    dataset_rows: int
    feature_count: int
    feature_names: list[str]
    split: MLDatasetSplitSummary
    validation_metrics: MLMetricsSummary
    test_metrics: MLMetricsSummary
    decision_threshold: float
    confidence_threshold: float
    dataset_path: str
    artifact_path: str
    metadata_path: str


class MLPredictRequest(BaseModel):
    exchange: str = Field(default="binance")
    symbol: str = Field(default="BTC/USDT")
    timeframe: str = Field(default="1h")
    limit: int = Field(default=300, ge=250, le=5000)
    model_id: str | None = None
    target: MLTarget = Field(default=MLTarget.FUTURE_EDGE_LONG)
    forecast_horizon_candles: int = Field(default=3, ge=1, le=24)
    min_edge_percent: float = Field(default=0.4, ge=0.05, le=5.0)
    confidence_threshold: float | None = Field(default=None, ge=0.5, le=0.99)


class MLPredictResponse(BaseModel):
    model_id: str
    exchange: str
    symbol: str
    timeframe: str
    target: MLTarget
    forecast_horizon_candles: int
    min_edge_percent: float
    min_precision: float
    advisory_signal: MLAdvisorySignal
    probability_up: float
    probability_down: float
    confidence: float
    decision_threshold: float
    passes_decision_threshold: bool
    passes_confidence_threshold: bool
    confidence_threshold: float
    feature_open_time: datetime
    feature_close_time: datetime
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    feature_values: dict[str, float]


class MLModelSummary(BaseModel):
    model_id: str
    exchange: str
    symbol: str
    timeframe: str
    target: MLTarget
    forecast_horizon_candles: int
    min_edge_percent: float
    min_precision: float
    min_positive_predictions: int
    algorithm: str
    trained_at: datetime
    dataset_rows: int
    decision_threshold: float
    confidence_threshold: float


class MLWalkForwardRequest(BaseModel):
    exchange: str = Field(default="binance")
    symbol: str = Field(default="BTC/USDT")
    timeframe: str = Field(default="1h")
    limit: int = Field(default=3000, ge=500, le=5000)
    target: MLTarget = Field(default=MLTarget.FUTURE_EDGE_LONG)
    forecast_horizon_candles: int = Field(default=3, ge=1, le=24)
    min_edge_percent: float = Field(default=0.4, ge=0.05, le=5.0)
    min_precision: float | None = Field(default=None, ge=0.05, le=0.99)
    min_positive_predictions: int | None = Field(default=None, ge=1, le=2000)
    training_window_rows: int = Field(default=1200, ge=200, le=4000)
    validation_window_rows: int = Field(default=300, ge=50, le=1500)
    test_window_rows: int = Field(default=300, ge=50, le=1500)
    step_rows: int = Field(default=300, ge=25, le=1500)
    confidence_threshold: float | None = Field(default=None, ge=0.5, le=0.99)


class MLWalkForwardWindow(BaseModel):
    window_index: int
    train_start: datetime
    train_end: datetime
    validation_start: datetime
    validation_end: datetime
    test_start: datetime
    test_end: datetime
    algorithm: str
    decision_threshold: float
    train_rows: int
    validation_rows: int
    test_rows: int
    validation_metrics: MLMetricsSummary
    test_metrics: MLMetricsSummary


class MLWalkForwardSummary(BaseModel):
    windows: int
    average_validation_accuracy: float
    average_validation_roc_auc: float | None = None
    average_test_accuracy: float
    average_test_precision: float
    average_test_recall: float
    average_test_f1: float
    average_test_roc_auc: float | None = None


class MLWalkForwardResponse(BaseModel):
    exchange: str
    symbol: str
    timeframe: str
    target: MLTarget
    forecast_horizon_candles: int
    min_edge_percent: float
    min_precision: float
    min_positive_predictions: int
    confidence_threshold: float
    dataset_rows: int
    feature_count: int
    feature_names: list[str]
    training_window_rows: int
    validation_window_rows: int
    test_window_rows: int
    step_rows: int
    summary: MLWalkForwardSummary
    windows: list[MLWalkForwardWindow]
