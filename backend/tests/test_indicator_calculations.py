from app.services.indicators.calculations import atr, ema, macd, rsi


def test_ema_returns_none_until_seed_period_then_values():
    values = [1, 2, 3, 4, 5]

    result = ema(values, period=3)

    assert result[:2] == [None, None]
    assert result[2] == 2.0
    assert round(result[3], 4) == 3.0
    assert round(result[4], 4) == 4.0


def test_rsi_returns_high_value_for_consistent_uptrend():
    closes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

    result = rsi(closes, period=14)

    assert result[13] is None
    assert result[14] == 100.0


def test_macd_returns_series_of_equal_length():
    closes = list(range(1, 60))

    macd_line, signal_line, histogram = macd(closes)

    assert len(macd_line) == len(closes)
    assert len(signal_line) == len(closes)
    assert len(histogram) == len(closes)
    assert macd_line[-1] is not None
    assert signal_line[-1] is not None
    assert histogram[-1] is not None


def test_atr_returns_values_after_warmup_period():
    highs = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
    lows = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
    closes = [9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5, 20.5, 21.5, 22.5, 23.5]

    result = atr(highs, lows, closes, period=14)

    assert result[12] is None
    assert result[13] is not None
    assert result[14] is not None


def test_ema_supports_long_trend_filter_series():
    values = list(range(1, 260))

    result = ema(values, period=200)

    assert result[198] is None
    assert result[199] is not None
    assert result[-1] is not None
