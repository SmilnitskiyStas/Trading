from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException

from app.schemas.market_data import MarketDataSyncRequest
from app.services.market_data.service import MarketDataService


def test_split_symbol_parses_base_and_quote():
    assert MarketDataService._split_symbol("BTC/USDT") == ("BTC", "USDT")


def test_split_symbol_rejects_invalid_format():
    try:
        MarketDataService._split_symbol("BTCUSDT")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Unsupported symbol format" in exc.detail
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected HTTPException for invalid symbol format")


def test_normalize_candle_row_maps_ohlcv_payload():
    row = MarketDataService._normalize_candle_row(
        trading_pair_id=1,
        timeframe="1h",
        item=[1715731200000, 100.0, 110.0, 95.0, 105.0, 1234.5],
    )

    assert row["trading_pair_id"] == 1
    assert row["timeframe"] == "1h"
    assert row["open_time"] == datetime(2024, 5, 15, 0, 0, tzinfo=UTC)
    assert row["open_price"] == Decimal("100.0")
    assert row["close_price"] == Decimal("105.0")


def test_sync_request_defaults_match_mvp_scope():
    payload = MarketDataSyncRequest()

    assert payload.exchange == "binance"
    assert payload.symbol == "BTC/USDT"
    assert payload.timeframe == "1h"


def test_sync_request_accepts_deeper_backfill_limit():
    payload = MarketDataSyncRequest(limit=5000)

    assert payload.limit == 5000


def test_timeframe_delta_supports_thirty_minutes():
    delta = MarketDataService._timeframe_delta("30m")

    assert delta.total_seconds() == 1800


def test_timeframe_delta_supports_fifteen_minutes():
    delta = MarketDataService._timeframe_delta("15m")

    assert delta.total_seconds() == 900


def test_timeframe_delta_rejects_unsupported_unit():
    try:
        MarketDataService._timeframe_delta("4x")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Unsupported timeframe" in exc.detail
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected HTTPException for invalid timeframe")


def test_automation_symbol_overrides_are_parseable():
    from app.core.config import get_settings

    settings = get_settings()

    assert settings.strategy_symbol_override_map["BTC/USDT"] == "rsi_ema_trend_v2"
    assert settings.strategy_symbol_override_map["ETH/USDT"] == "rsi_ema_trend_multi_v1"
