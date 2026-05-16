from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
import pytest

from app.schemas.ml import MLAdvisorySignal, MLPredictResponse, MLTarget
from app.schemas.indicators import IndicatorSnapshot
from app.schemas.risk import RiskEvaluationRequest
from app.schemas.strategy import StrategyEvaluationResponse, StrategySignal
from app.services.controls.runtime_state import runtime_control_state
from app.services.risk.service import RiskService

pytestmark = pytest.mark.asyncio


class StubStrategyService:
    def __init__(self, response: StrategyEvaluationResponse):
        self.response = response

    async def evaluate_strategy_inputs(self, **kwargs) -> StrategyEvaluationResponse:
        return self.response


class StubMLService:
    def __init__(self, response: MLPredictResponse | None = None, error: HTTPException | None = None):
        self.response = response
        self.error = error

    async def predict(self, payload) -> MLPredictResponse:
        if self.error is not None:
            raise self.error
        return self.response


def _strategy_response(signal: StrategySignal = StrategySignal.BUY, atr: float | None = 10.0) -> StrategyEvaluationResponse:
    snapshot = IndicatorSnapshot(
        open_time=datetime(2026, 5, 15, 0, 0, tzinfo=UTC),
        close_time=datetime(2026, 5, 15, 1, 0, tzinfo=UTC),
        close_price=Decimal("100"),
        ema_fast=99.0,
        ema_slow=98.0,
        ema_trend=97.0,
        rsi=30.0,
        macd=1.0,
        macd_signal=0.8,
        macd_histogram=0.2,
        atr=atr,
    )
    return StrategyEvaluationResponse(
        strategy_name="rsi_ema_trend_v1",
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        signal=signal,
        reasons=["stub"],
        candle_count=250,
        evaluated_at=datetime(2026, 5, 15, 1, 0, tzinfo=UTC),
        latest_close_price=Decimal("100"),
        latest_indicators=snapshot,
    )


def _ml_predict_response(
    advisory_signal: MLAdvisorySignal = MLAdvisorySignal.UP,
    passes_threshold: bool = True,
) -> MLPredictResponse:
    return MLPredictResponse(
        model_id="btc_usdt_1h_test",
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        target=MLTarget.NEXT_CLOSE_UP,
        advisory_signal=advisory_signal,
        probability_up=0.74 if advisory_signal == MLAdvisorySignal.UP else 0.31,
        probability_down=0.26 if advisory_signal == MLAdvisorySignal.UP else 0.69,
        confidence=0.74 if advisory_signal == MLAdvisorySignal.UP else 0.69,
        passes_confidence_threshold=passes_threshold,
        confidence_threshold=0.6,
        feature_open_time=datetime(2026, 5, 15, 0, 0, tzinfo=UTC),
        feature_close_time=datetime(2026, 5, 15, 1, 0, tzinfo=UTC),
        feature_values={"return_1": 0.01},
    )


async def test_risk_service_builds_trade_plan_for_valid_buy_signal():
    service = RiskService(StubStrategyService(_strategy_response()))
    payload = RiskEvaluationRequest()

    result = await service.evaluate(payload)

    assert result.allowed is True
    assert result.trade_plan is not None
    assert result.trade_plan.entry_price == Decimal("100")
    assert result.trade_plan.stop_loss_price is not None
    assert result.trade_plan.take_profit_price is not None
    assert result.trade_plan.position_size is not None


async def test_risk_service_blocks_trade_when_strategy_is_not_buy():
    service = RiskService(StubStrategyService(_strategy_response(signal=StrategySignal.HOLD)))
    payload = RiskEvaluationRequest()

    result = await service.evaluate(payload)

    assert result.allowed is False
    assert result.trade_plan is None
    assert any("Strategy signal is StrategySignal.HOLD" in reason for reason in result.reasons)


async def test_risk_service_blocks_trade_on_daily_loss_limit():
    service = RiskService(StubStrategyService(_strategy_response()))
    payload = RiskEvaluationRequest(current_daily_loss_percent=Decimal("5"))

    result = await service.evaluate(payload)

    assert result.allowed is False
    assert any("Daily loss limit" in reason for reason in result.reasons)


async def test_risk_service_returns_none_trade_plan_when_atr_missing():
    service = RiskService(StubStrategyService(_strategy_response(atr=None)))
    payload = RiskEvaluationRequest()

    result = await service.evaluate(payload)

    assert result.allowed is False
    assert result.trade_plan is None


async def test_risk_service_blocks_new_entries_when_kill_switch_is_active():
    runtime_control_state.enable_kill_switch("Manual safety stop.")
    try:
        service = RiskService(StubStrategyService(_strategy_response()))
        payload = RiskEvaluationRequest()

        result = await service.evaluate(payload)

        assert result.allowed is False
        assert result.trade_plan is None
        assert any("Emergency kill switch is active" in reason for reason in result.reasons)
    finally:
        runtime_control_state.disable_kill_switch()


async def test_risk_service_blocks_entry_when_ml_filter_disagrees():
    service = RiskService(
        StubStrategyService(_strategy_response()),
        ml_service=StubMLService(_ml_predict_response(advisory_signal=MLAdvisorySignal.DOWN)),
    )
    payload = RiskEvaluationRequest()
    original_enabled = service.settings.ml_risk_filter_enabled
    original_require_model = service.settings.ml_risk_filter_require_model
    try:
        service.settings.ml_risk_filter_enabled = True
        service.settings.ml_risk_filter_require_model = False
        result = await service.evaluate(payload)
    finally:
        service.settings.ml_risk_filter_enabled = original_enabled
        service.settings.ml_risk_filter_require_model = original_require_model

    assert result.allowed is False
    assert result.trade_plan is None
    assert result.ml_filter is not None
    assert result.ml_filter.available is True
    assert result.ml_filter.advisory_signal == MLAdvisorySignal.DOWN
    assert any("ML confidence filter did not confirm" in reason for reason in result.reasons)


async def test_risk_service_allows_entry_when_ml_model_is_unavailable_and_not_required():
    service = RiskService(
        StubStrategyService(_strategy_response()),
        ml_service=StubMLService(error=HTTPException(status_code=404, detail="No trained ML model found.")),
    )
    payload = RiskEvaluationRequest()
    original_enabled = service.settings.ml_risk_filter_enabled
    original_require_model = service.settings.ml_risk_filter_require_model
    try:
        service.settings.ml_risk_filter_enabled = True
        service.settings.ml_risk_filter_require_model = False
        result = await service.evaluate(payload)
    finally:
        service.settings.ml_risk_filter_enabled = original_enabled
        service.settings.ml_risk_filter_require_model = original_require_model

    assert result.allowed is True
    assert result.trade_plan is not None
    assert result.ml_filter is not None
    assert result.ml_filter.available is False
