from app.schemas.indicators import IndicatorSnapshot
from app.schemas.strategy import StrategySignal


class RsiEmaTrendStrategy:
    def __init__(
        self,
        name: str,
        trend_period: int,
        buy_rsi_max: float,
        sell_rsi_min: float,
        require_macd_improving: bool,
    ):
        self.name = name
        self.trend_period = trend_period
        self.buy_rsi_max = buy_rsi_max
        self.sell_rsi_min = sell_rsi_min
        self.require_macd_improving = require_macd_improving

    def evaluate(
        self,
        latest: IndicatorSnapshot,
        previous: IndicatorSnapshot | None,
    ) -> tuple[StrategySignal, list[str]]:
        reasons: list[str] = []
        trend_value = self._resolve_trend_value(latest)

        if trend_value is None or latest.ema_slow is None or latest.rsi is None or latest.macd_histogram is None:
            return StrategySignal.HOLD, [f"Not enough candle history to evaluate EMA{self.trend_period}/EMA50/RSI/MACD."]

        macd_is_improving = False
        if previous is not None and previous.macd_histogram is not None:
            macd_is_improving = latest.macd_histogram > previous.macd_histogram

        price_above_trend = float(latest.close_price) > trend_value
        price_below_exit_filter = float(latest.close_price) < latest.ema_slow
        rsi_buy_zone = latest.rsi < self.buy_rsi_max
        rsi_sell_zone = latest.rsi > self.sell_rsi_min

        if price_above_trend:
            reasons.append(f"Close is above EMA{self.trend_period} trend filter.")
        else:
            reasons.append(f"Close is not above EMA{self.trend_period} trend filter.")

        if rsi_buy_zone:
            reasons.append(f"RSI is below {self.buy_rsi_max:g}.")
        elif rsi_sell_zone:
            reasons.append(f"RSI is above {self.sell_rsi_min:g}.")
        else:
            reasons.append("RSI is in the neutral zone.")

        if macd_is_improving:
            reasons.append("MACD histogram is improving.")
        else:
            reasons.append("MACD histogram is not improving.")

        if price_below_exit_filter:
            reasons.append("Close is below EMA50 exit filter.")

        entry_macd_condition = macd_is_improving or not self.require_macd_improving

        if price_above_trend and rsi_buy_zone and entry_macd_condition:
            return StrategySignal.BUY, reasons

        if rsi_sell_zone and price_below_exit_filter:
            return StrategySignal.SELL, reasons

        return StrategySignal.HOLD, reasons

    def _resolve_trend_value(self, snapshot: IndicatorSnapshot) -> float | None:
        if snapshot.ema_by_period is not None and self.trend_period in snapshot.ema_by_period:
            return snapshot.ema_by_period[self.trend_period]
        return snapshot.ema_trend
