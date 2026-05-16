from datetime import UTC, datetime

from app.core.config import get_settings
from app.schemas.ml import MLModelDetailResponse, MLTarget
from app.services.ml.service import MLService


def test_ml_checklist_requires_review_precision_and_profit(monkeypatch):
    monkeypatch.setenv("ML_EVAL_MIN_CLOSED_TRADES", "5")
    monkeypatch.setenv("ML_EVAL_MIN_PROFIT_FACTOR", "1.05")
    monkeypatch.setenv("ML_EVAL_MAX_DRAWDOWN_PERCENT", "12")
    monkeypatch.setenv("ML_EVAL_MIN_TEST_PRECISION", "0.35")
    monkeypatch.setenv("ML_EVAL_ALLOWED_REVIEW_STATUSES", "approved_for_paper_gate,approved")
    get_settings.cache_clear()

    service = MLService(indicator_service=None)  # type: ignore[arg-type]
    detail = MLModelDetailResponse(
        model_id="btc_model",
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        target=MLTarget.FUTURE_EDGE_LONG,
        algorithm="random_forest_v1_1",
        trained_at=datetime(2026, 5, 16, tzinfo=UTC),
        dataset_rows=500,
        test_metrics={"precision": 0.41},
        review_status="approved_for_paper_gate",
    )

    response = service.build_evaluation_checklist(
        model_detail=detail,
        account_name="paper-main",
        closed_trades=7,
        profit_factor=1.20,
        max_drawdown_percent=8.5,
    )

    assert response.overall_passed is True
    assert response.recommendation == "READY_FOR_PAPER_GATE"
