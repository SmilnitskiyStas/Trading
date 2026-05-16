from __future__ import annotations


def ema(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("EMA period must be positive.")

    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result

    multiplier = 2 / (period + 1)
    seed = sum(values[:period]) / period
    result[period - 1] = seed
    previous = seed

    for index in range(period, len(values)):
        current = (values[index] - previous) * multiplier + previous
        result[index] = current
        previous = current

    return result


def rsi(closes: list[float], period: int = 14) -> list[float | None]:
    if period <= 0:
        raise ValueError("RSI period must be positive.")

    result: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return result

    gains: list[float] = []
    losses: list[float] = []

    for index in range(1, period + 1):
        delta = closes[index] - closes[index - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period
    result[period] = _rsi_value(average_gain, average_loss)

    for index in range(period + 1, len(closes)):
        delta = closes[index] - closes[index - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)

        average_gain = ((average_gain * (period - 1)) + gain) / period
        average_loss = ((average_loss * (period - 1)) + loss) / period
        result[index] = _rsi_value(average_gain, average_loss)

    return result


def macd(
    closes: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    fast_ema = ema(closes, fast_period)
    slow_ema = ema(closes, slow_period)

    macd_line: list[float | None] = []
    for fast_value, slow_value in zip(fast_ema, slow_ema, strict=False):
        if fast_value is None or slow_value is None:
            macd_line.append(None)
        else:
            macd_line.append(fast_value - slow_value)

    numeric_macd = [value for value in macd_line if value is not None]
    signal_values = ema(numeric_macd, signal_period)

    signal_line: list[float | None] = [None] * len(macd_line)
    signal_start = next((idx for idx, value in enumerate(macd_line) if value is not None), None)
    if signal_start is not None:
        for offset, value in enumerate(signal_values):
            signal_line[signal_start + offset] = value

    histogram: list[float | None] = []
    for macd_value, signal_value in zip(macd_line, signal_line, strict=False):
        if macd_value is None or signal_value is None:
            histogram.append(None)
        else:
            histogram.append(macd_value - signal_value)

    return macd_line, signal_line, histogram


def atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> list[float | None]:
    if period <= 0:
        raise ValueError("ATR period must be positive.")

    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("ATR inputs must be the same length.")

    true_ranges: list[float] = []
    for index in range(len(closes)):
        if index == 0:
            true_ranges.append(highs[index] - lows[index])
            continue

        current_high = highs[index]
        current_low = lows[index]
        previous_close = closes[index - 1]
        true_ranges.append(
            max(
                current_high - current_low,
                abs(current_high - previous_close),
                abs(current_low - previous_close),
            )
        )

    result: list[float | None] = [None] * len(closes)
    if len(true_ranges) < period:
        return result

    initial_atr = sum(true_ranges[:period]) / period
    result[period - 1] = initial_atr
    previous = initial_atr

    for index in range(period, len(true_ranges)):
        current = ((previous * (period - 1)) + true_ranges[index]) / period
        result[index] = current
        previous = current

    return result


def _rsi_value(average_gain: float, average_loss: float) -> float:
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))
