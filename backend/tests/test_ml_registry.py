import json

from app.core.config import get_settings
from app.services.ml.registry import MLModelRegistry


def test_registry_prefers_pinned_model(monkeypatch, tmp_path):
    models_dir = tmp_path / "models"
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("ML_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("ML_DATASETS_DIR", str(datasets_dir))
    get_settings.cache_clear()

    registry = MLModelRegistry()
    _write_metadata(registry, "btc_usdt_1h_old", "BTC/USDT", "1h")
    _write_metadata(registry, "btc_usdt_1h_new", "BTC/USDT", "1h")

    registry.pin_model(symbol="BTC/USDT", timeframe="1h", model_id="btc_usdt_1h_old")

    assert registry.resolve_model_id(model_id=None, symbol="BTC/USDT", timeframe="1h") == "btc_usdt_1h_old"


def test_registry_unpin_falls_back_to_latest(monkeypatch, tmp_path):
    models_dir = tmp_path / "models"
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("ML_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("ML_DATASETS_DIR", str(datasets_dir))
    get_settings.cache_clear()

    registry = MLModelRegistry()
    _write_metadata(registry, "btc_usdt_1h_20260101", "BTC/USDT", "1h")
    _write_metadata(registry, "btc_usdt_1h_20260102", "BTC/USDT", "1h")
    registry.pin_model(symbol="BTC/USDT", timeframe="1h", model_id="btc_usdt_1h_20260101")

    resolved = registry.unpin_model(symbol="BTC/USDT", timeframe="1h")

    assert resolved["selection_mode"] == "latest"
    assert registry.resolve_model_id(model_id=None, symbol="BTC/USDT", timeframe="1h") == "btc_usdt_1h_20260102"


def test_registry_update_metadata_persists_review_fields(monkeypatch, tmp_path):
    models_dir = tmp_path / "models"
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("ML_MODELS_DIR", str(models_dir))
    monkeypatch.setenv("ML_DATASETS_DIR", str(datasets_dir))
    get_settings.cache_clear()

    registry = MLModelRegistry()
    _write_metadata(registry, "btc_usdt_1h_review", "BTC/USDT", "1h")

    updated = registry.update_metadata(
        "btc_usdt_1h_review",
        {
            "review_status": "approved_for_paper_gate",
            "review_notes": "Stable enough after walk-forward review.",
        },
    )

    assert updated["review_status"] == "approved_for_paper_gate"
    assert registry.load_metadata("btc_usdt_1h_review")["review_notes"] == "Stable enough after walk-forward review."


def _write_metadata(registry: MLModelRegistry, model_id: str, symbol: str, timeframe: str) -> None:
    registry.metadata_path(model_id).write_text(
        json.dumps(
            {
                "model_id": model_id,
                "exchange": "binance",
                "symbol": symbol,
                "timeframe": timeframe,
                "target": "future_edge_long",
                "algorithm": "logistic_regression_v1_1",
                "trained_at": "2026-05-16T12:00:00+00:00",
                "dataset_rows": 500,
                "confidence_threshold": 0.6,
                "decision_threshold": 0.4,
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
