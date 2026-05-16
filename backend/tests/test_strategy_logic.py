from datetime import UTC, datetime
from decimal import Decimal

from app.schemas.indicators import IndicatorSnapshot
from app.schemas.strategy import StrategySignal
from app.services.strategies.rsi_ema_trend import RsiEmaTrendStrategy


def _snapshot(
    close_price: str,
    ema_slow: float | None,
    ema_trend: float | None,
    rsi: float | None,
    macd_histogram: float | None,
) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        open_time=datetime(2026, 5, 15, 0, 0, tzinfo=UTC),
        close_time=datetime(2026, 5, 15, 1, 0, tzinfo=UTC),
        close_price=Decimal(close_price),
        ema_fast=100.0,
        ema_slow=ema_slow,
        ema_trend=ema_trend,
        rsi=rsi,
        macd=0.5,
        macd_signal=0.4,
        macd_histogram=macd_histogram,
        atr=2.0,
    )


def test_strategy_returns_buy_when_all_entry_conditions_match():
    strategy = RsiEmaTrendStrategy(
        name="test",
        trend_period=200,
        buy_rsi_max=35,
        sell_rsi_min=65,
        require_macd_improving=True,
    )
    previous = _snapshot("101", ema_slow=100.0, ema_trend=99.0, rsi=34.0, macd_histogram=0.10)
    latest = _snapshot("105", ema_slow=101.0, ema_trend=100.0, rsi=30.0, macd_histogram=0.25)

    signal, reasons = strategy.evaluate(latest=latest, previous=previous)

    assert signal == StrategySignal.BUY
    assert "Close is above EMA200 trend filter." in reasons
    assert "RSI is below 35." in reasons
    assert "MACD histogram is improving." in reasons


def test_strategy_returns_sell_when_exit_conditions_match():
    strategy = RsiEmaTrendStrategy(
        name="test",
        trend_period=200,
        buy_rsi_max=35,
        sell_rsi_min=65,
        require_macd_improving=True,
    )
    previous = _snapshot("99", ema_slow=100.0, ema_trend=105.0, rsi=60.0, macd_histogram=0.05)
    latest = _snapshot("95", ema_slow=100.0, ema_trend=104.0, rsi=70.0, macd_histogram=0.01)

    signal, reasons = strategy.evaluate(latest=latest, previous=previous)

    assert signal == StrategySignal.SELL
    assert "RSI is above 65." in reasons
    assert "Close is below EMA50 exit filter." in reasons


def test_strategy_returns_hold_when_signal_is_incomplete():
    strategy = RsiEmaTrendStrategy(
        name="test",
        trend_period=200,
        buy_rsi_max=35,
        sell_rsi_min=65,
        require_macd_improving=True,
    )
    latest = _snapshot("100", ema_slow=None, ema_trend=None, rsi=None, macd_histogram=None)

    signal, reasons = strategy.evaluate(latest=latest, previous=None)

    assert signal == StrategySignal.HOLD
    assert reasons == ["Not enough candle history to evaluate EMA200/EMA50/RSI/MACD."]


def test_tuned_strategy_can_buy_without_macd_improvement_requirement():
    strategy = RsiEmaTrendStrategy(
        name="test-v2",
        trend_period=200,
        buy_rsi_max=40,
        sell_rsi_min=58,
        require_macd_improving=False,
    )
    previous = _snapshot("100", ema_slow=98.0, ema_trend=95.0, rsi=39.0, macd_histogram=0.20)
    latest = _snapshot("101", ema_slow=99.0, ema_trend=96.0, rsi=39.5, macd_histogram=0.10)

    signal, reasons = strategy.evaluate(latest=latest, previous=previous)

    assert signal == StrategySignal.BUY
    assert "MACD histogram is not improving." in reasons


def test_multi_strategy_uses_its_configured_trend_period():
    strategy = RsiEmaTrendStrategy(
        name="test-multi",
        trend_period=100,
        buy_rsi_max=40,
        sell_rsi_min=58,
        require_macd_improving=False,
    )
    previous = _snapshot("98", ema_slow=97.0, ema_trend=110.0, rsi=39.0, macd_histogram=0.10)
    latest = _snapshot("101", ema_slow=99.0, ema_trend=120.0, rsi=35.0, macd_histogram=0.05)
    previous.ema_by_period = {100: 97.0, 200: 110.0}
    latest.ema_by_period = {100: 100.0, 200: 120.0}

    signal, reasons = strategy.evaluate(latest=latest, previous=previous)

    assert signal == StrategySignal.BUY
    assert "Close is above EMA100 trend filter." in reasons
