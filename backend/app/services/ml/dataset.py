from dataclasses import dataclass
from datetime import datetime
from math import cos, pi, sin
from pathlib import Path
import csv

from app.schemas.indicators import IndicatorSnapshot
from app.schemas.ml import MLTarget


@dataclass(slots=True)
class MLFeatureRow:
    open_time: datetime
    close_time: datetime
    features: dict[str, float]
    target_up: int


@dataclass(slots=True)
class MLDataset:
    rows: list[MLFeatureRow]
    feature_names: list[str]


@dataclass(slots=True)
class MLDatasetSplit:
    train_rows: list[MLFeatureRow]
    validation_rows: list[MLFeatureRow]
    test_rows: list[MLFeatureRow]


class MLDatasetBuilder:
    FEATURE_NAMES = [
        "return_1",
        "return_2",
        "return_3",
        "range_percent",
        "body_percent",
        "upper_wick_percent",
        "lower_wick_percent",
        "volume",
        "volume_change_1",
        "ema_fast_gap",
        "ema_slow_gap",
        "ema_trend_gap",
        "ema_fast_slow_gap",
        "ema_fast_slope",
        "ema_slow_slope",
        "ema_trend_slope",
        "rsi",
        "rsi_delta",
        "rsi_centered",
        "macd",
        "macd_signal",
        "macd_histogram",
        "macd_histogram_delta",
        "atr_percent",
        "atr_change_1",
        "distance_to_prev_high",
        "distance_to_prev_low",
        "three_candle_momentum",
        "hour_sin",
        "hour_cos",
        "weekday_sin",
        "weekday_cos",
    ]

    @classmethod
    def build_training_dataset(
        cls,
        candles,
        indicators: list[IndicatorSnapshot],
        target: MLTarget,
        forecast_horizon_candles: int,
        min_edge_percent: float,
    ) -> MLDataset:
        rows: list[MLFeatureRow] = []
        candle_count = min(len(candles), len(indicators))
        if candle_count < 4 + forecast_horizon_candles:
            return MLDataset(rows=[], feature_names=cls.FEATURE_NAMES.copy())

        max_index = candle_count - forecast_horizon_candles
        for index in range(3, max_index):
            features = cls._build_feature_map(candles=candles, indicators=indicators, index=index)
            if features is None:
                continue

            target_up = cls._resolve_target(
                candles=candles,
                index=index,
                target=target,
                forecast_horizon_candles=forecast_horizon_candles,
                min_edge_percent=min_edge_percent,
            )
            rows.append(
                MLFeatureRow(
                    open_time=candles[index].open_time,
                    close_time=candles[index].close_time,
                    features=features,
                    target_up=target_up,
                )
            )

        return MLDataset(rows=rows, feature_names=cls.FEATURE_NAMES.copy())

    @classmethod
    def build_latest_feature_row(cls, candles, indicators: list[IndicatorSnapshot]) -> MLFeatureRow | None:
        candle_count = min(len(candles), len(indicators))
        if candle_count < 4:
            return None

        index = candle_count - 1
        features = cls._build_feature_map(candles=candles, indicators=indicators, index=index)
        if features is None:
            return None

        return MLFeatureRow(
            open_time=candles[index].open_time,
            close_time=candles[index].close_time,
            features=features,
            target_up=0,
        )

    @staticmethod
    def split_rows(
        rows: list[MLFeatureRow],
        train_ratio: float,
        validation_ratio: float,
    ) -> MLDatasetSplit:
        total_rows = len(rows)
        train_end = int(total_rows * train_ratio)
        validation_end = train_end + int(total_rows * validation_ratio)

        return MLDatasetSplit(
            train_rows=rows[:train_end],
            validation_rows=rows[train_end:validation_end],
            test_rows=rows[validation_end:],
        )

    @staticmethod
    def export_csv(path: Path, dataset: MLDataset) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["open_time", "close_time", *dataset.feature_names, "target_up"])
            for row in dataset.rows:
                writer.writerow(
                    [
                        row.open_time.isoformat(),
                        row.close_time.isoformat(),
                        *[row.features[name] for name in dataset.feature_names],
                        row.target_up,
                    ]
                )

    @classmethod
    def _build_feature_map(cls, candles, indicators: list[IndicatorSnapshot], index: int) -> dict[str, float] | None:
        previous_three_candle = candles[index - 3]
        previous_two_candle = candles[index - 2]
        previous_candle = candles[index - 1]
        candle = candles[index]
        previous_indicator = indicators[index - 1]
        previous_two_indicator = indicators[index - 2]
        indicator = indicators[index]

        previous_three_close = float(previous_three_candle.close_price)
        previous_two_close = float(previous_two_candle.close_price)
        previous_close = float(previous_candle.close_price)
        open_price = float(candle.open_price)
        high_price = float(candle.high_price)
        low_price = float(candle.low_price)
        close_price = float(candle.close_price)
        volume = float(candle.volume)
        previous_volume = float(previous_candle.volume)

        if (
            previous_three_close <= 0
            or previous_two_close <= 0
            or previous_close <= 0
            or open_price <= 0
            or close_price <= 0
            or previous_volume <= 0
        ):
            return None

        if (
            indicator.ema_fast is None
            or indicator.ema_slow is None
            or indicator.ema_trend is None
            or indicator.rsi is None
            or indicator.macd is None
            or indicator.macd_signal is None
            or indicator.macd_histogram is None
            or indicator.atr is None
            or previous_indicator.ema_fast is None
            or previous_indicator.ema_slow is None
            or previous_indicator.ema_trend is None
            or previous_indicator.rsi is None
            or previous_indicator.macd_histogram is None
            or previous_indicator.atr is None
            or previous_two_indicator.rsi is None
        ):
            return None

        candle_range = max(high_price - low_price, 0.0)
        candle_body = close_price - open_price
        upper_wick = max(high_price - max(open_price, close_price), 0.0)
        lower_wick = max(min(open_price, close_price) - low_price, 0.0)
        hour_fraction = (candle.open_time.hour % 24) / 24
        weekday_fraction = candle.open_time.weekday() / 7
        previous_high = float(previous_candle.high_price)
        previous_low = float(previous_candle.low_price)

        return {
            "return_1": (close_price - previous_close) / previous_close,
            "return_2": (close_price - previous_two_close) / previous_two_close,
            "return_3": (close_price - previous_three_close) / previous_three_close,
            "range_percent": candle_range / close_price,
            "body_percent": candle_body / open_price,
            "upper_wick_percent": upper_wick / close_price,
            "lower_wick_percent": lower_wick / close_price,
            "volume": volume,
            "volume_change_1": (volume - previous_volume) / previous_volume,
            "ema_fast_gap": (close_price - indicator.ema_fast) / indicator.ema_fast,
            "ema_slow_gap": (close_price - indicator.ema_slow) / indicator.ema_slow,
            "ema_trend_gap": (close_price - indicator.ema_trend) / indicator.ema_trend,
            "ema_fast_slow_gap": (indicator.ema_fast - indicator.ema_slow) / indicator.ema_slow,
            "ema_fast_slope": (indicator.ema_fast - previous_indicator.ema_fast) / previous_indicator.ema_fast,
            "ema_slow_slope": (indicator.ema_slow - previous_indicator.ema_slow) / previous_indicator.ema_slow,
            "ema_trend_slope": (indicator.ema_trend - previous_indicator.ema_trend) / previous_indicator.ema_trend,
            "rsi": indicator.rsi / 100.0,
            "rsi_delta": (indicator.rsi - previous_indicator.rsi) / 100.0,
            "rsi_centered": (indicator.rsi - 50.0) / 50.0,
            "macd": indicator.macd,
            "macd_signal": indicator.macd_signal,
            "macd_histogram": indicator.macd_histogram,
            "macd_histogram_delta": indicator.macd_histogram - previous_indicator.macd_histogram,
            "atr_percent": indicator.atr / close_price,
            "atr_change_1": (indicator.atr - previous_indicator.atr) / previous_indicator.atr,
            "distance_to_prev_high": (close_price - previous_high) / previous_high,
            "distance_to_prev_low": (close_price - previous_low) / previous_low,
            "three_candle_momentum": (
                ((close_price - previous_close) / previous_close)
                + ((previous_close - previous_two_close) / previous_two_close)
                + ((previous_two_close - previous_three_close) / previous_three_close)
            ),
            "hour_sin": sin(2 * pi * hour_fraction),
            "hour_cos": cos(2 * pi * hour_fraction),
            "weekday_sin": sin(2 * pi * weekday_fraction),
            "weekday_cos": cos(2 * pi * weekday_fraction),
        }

    @staticmethod
    def _resolve_target(
        candles,
        index: int,
        target: MLTarget,
        forecast_horizon_candles: int,
        min_edge_percent: float,
    ) -> int:
        current_close = float(candles[index].close_price)
        future_candles = candles[index + 1:index + 1 + forecast_horizon_candles]
        if not future_candles:
            return 0

        if target == MLTarget.NEXT_CLOSE_UP:
            return 1 if float(future_candles[0].close_price) > current_close else 0

        edge_multiplier = min_edge_percent / 100.0
        future_max_high = max(float(candle.high_price) for candle in future_candles)
        future_min_low = min(float(candle.low_price) for candle in future_candles)
        upside_level = current_close * (1.0 + edge_multiplier)
        downside_guard = current_close * (1.0 - edge_multiplier)

        return 1 if future_max_high >= upside_level and future_min_low > downside_guard else 0
