from datetime import UTC, datetime

import numpy as np

from app.schemas.indicators import IndicatorSnapshot
from app.schemas.ml import MLAdvisorySignal, MLTarget
from app.schemas.ml import MLMetricsSummary
from app.services.ml.dataset import MLFeatureRow, MLDatasetBuilder
from app.services.ml.service import MLService


def test_ml_split_is_chronological():
    rows = [
        MLFeatureRow(
            open_time=datetime(2026, 1, day, tzinfo=UTC),
            close_time=datetime(2026, 1, day, 1, tzinfo=UTC),
            features={"x": float(day)},
            target_up=day % 2,
        )
        for day in range(1, 11)
    ]

    split = MLDatasetBuilder.split_rows(rows=rows, train_ratio=0.6, validation_ratio=0.2)

    assert [row.features["x"] for row in split.train_rows] == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    assert [row.features["x"] for row in split.validation_rows] == [7.0, 8.0]
    assert [row.features["x"] for row in split.test_rows] == [9.0, 10.0]


def test_ml_advisory_signal_respects_confidence_threshold():
    assert MLService.resolve_advisory_signal(0.82, 0.55, 0.60) == (MLAdvisorySignal.UP, 0.82, True, True)
    assert MLService.resolve_advisory_signal(0.23, 0.55, 0.60) == (MLAdvisorySignal.DOWN, 0.77, False, True)
    assert MLService.resolve_advisory_signal(0.56, 0.55, 0.60) == (MLAdvisorySignal.HOLD, 0.56, True, False)


def test_ml_v1_1_feature_set_contains_richer_regime_features():
    assert "return_3" in MLDatasetBuilder.FEATURE_NAMES
    assert "volume_change_1" in MLDatasetBuilder.FEATURE_NAMES
    assert "ema_fast_slope" in MLDatasetBuilder.FEATURE_NAMES
    assert "rsi_delta" in MLDatasetBuilder.FEATURE_NAMES
    assert "macd_histogram_delta" in MLDatasetBuilder.FEATURE_NAMES
    assert "three_candle_momentum" in MLDatasetBuilder.FEATURE_NAMES


def test_model_selection_score_rewards_positive_class_quality():
    stronger = MLMetricsSummary(
        accuracy=0.51,
        precision=0.58,
        recall=0.55,
        f1_score=0.56,
        positive_rate=0.48,
        roc_auc=0.61,
    )
    weaker = MLMetricsSummary(
        accuracy=0.56,
        precision=0.36,
        recall=0.30,
        f1_score=0.33,
        positive_rate=0.48,
        roc_auc=0.61,
    )
    assert MLService._model_selection_score(stronger) > MLService._model_selection_score(weaker)


def test_walk_forward_window_builder_creates_sequential_windows():
    windows = MLService._build_walk_forward_windows(
        total_rows=1200,
        training_window_rows=400,
        validation_window_rows=100,
        test_window_rows=100,
        step_rows=100,
    )

    assert len(windows) == 7
    assert windows[0] == {
        "train_start": 0,
        "train_end": 400,
        "validation_start": 400,
        "validation_end": 500,
        "test_start": 500,
        "test_end": 600,
    }
    assert windows[1]["train_start"] == 100
    assert windows[-1]["test_end"] == 1200


def test_decision_threshold_search_can_move_below_default_half():
    probabilities = np.array([0.42, 0.44, 0.46, 0.70, 0.30, 0.41])
    targets = np.array([1, 1, 0, 1, 0, 1])

    threshold = MLService._find_best_decision_threshold(probabilities, targets)

    assert 0.30 <= threshold <= 0.74
    assert threshold != 0.5


def test_decision_threshold_search_can_enforce_minimum_precision_floor():
    probabilities = np.array([0.92, 0.81, 0.78, 0.64, 0.58, 0.54, 0.49, 0.35])
    targets = np.array([1, 0, 1, 0, 1, 0, 0, 0])

    unconstrained_threshold = MLService._find_best_decision_threshold_with_floor(
        probabilities=probabilities,
        targets=targets,
        min_precision=0.0,
    )
    constrained_threshold = MLService._find_best_decision_threshold_with_floor(
        probabilities=probabilities,
        targets=targets,
        min_precision=0.6,
    )

    assert constrained_threshold >= unconstrained_threshold


def test_decision_threshold_search_can_enforce_minimum_positive_predictions_floor():
    probabilities = np.array([0.93, 0.88, 0.79, 0.61, 0.55, 0.49, 0.43, 0.39, 0.34, 0.31])
    targets = np.array([1, 0, 1, 0, 1, 0, 1, 0, 0, 0])

    unconstrained_threshold = MLService._find_best_decision_threshold_with_floor(
        probabilities=probabilities,
        targets=targets,
        min_precision=0.4,
        min_positive_predictions=0,
    )
    constrained_threshold = MLService._find_best_decision_threshold_with_floor(
        probabilities=probabilities,
        targets=targets,
        min_precision=0.4,
        min_positive_predictions=5,
    )

    assert constrained_threshold <= unconstrained_threshold


def test_decision_threshold_search_falls_back_when_precision_floor_is_unreachable():
    probabilities = np.array([0.71, 0.68, 0.62, 0.57, 0.51, 0.45])
    targets = np.array([1, 0, 1, 0, 1, 0])

    threshold = MLService._find_best_decision_threshold_with_floor(
        probabilities=probabilities,
        targets=targets,
        min_precision=0.95,
        min_positive_predictions=10,
    )

    assert 0.30 <= threshold <= 0.74


def test_future_edge_long_target_is_positive_when_upside_beats_edge_and_drawdown_stays_small():
    candles = [
        _candle(100, 101, 99, 100, 1000, hour=0),
        _candle(100, 102, 99, 101, 1100, hour=1),
        _candle(101, 103, 100, 102, 1050, hour=2),
        _candle(102, 104, 101, 103, 1150, hour=3),
        _candle(103, 104, 102.8, 103.6, 1200, hour=4),
        _candle(103.6, 104.2, 103.1, 104.0, 1250, hour=5),
        _candle(104.0, 104.5, 103.5, 104.1, 1300, hour=6),
    ]
    indicators = [_indicator(candle.close_price, offset=index) for index, candle in enumerate(candles)]

    dataset = MLDatasetBuilder.build_training_dataset(
        candles=candles,
        indicators=indicators,
        target=MLTarget.FUTURE_EDGE_LONG,
        forecast_horizon_candles=2,
        min_edge_percent=0.4,
    )

    assert len(dataset.rows) == 2
    assert dataset.rows[0].target_up == 1


def test_latest_feature_row_uses_last_available_candle():
    candles = [
        _candle(100, 101, 99, 100, 1000, hour=0),
        _candle(100, 102, 99, 101, 1100, hour=1),
        _candle(101, 103, 100, 102, 1050, hour=2),
        _candle(102, 104, 101, 103, 1150, hour=3),
        _candle(103, 105, 102, 104, 1200, hour=4),
    ]
    indicators = [_indicator(candle.close_price, offset=index) for index, candle in enumerate(candles)]

    row = MLDatasetBuilder.build_latest_feature_row(candles=candles, indicators=indicators)

    assert row is not None
    assert row.open_time == candles[-1].open_time
    assert row.close_time == candles[-1].close_time
    assert "three_candle_momentum" in row.features


def _candle(open_price: float, high_price: float, low_price: float, close_price: float, volume: float, hour: int):
    class CandleStub:
        def __init__(self):
            self.open_time = datetime(2026, 1, 1, hour, 0, tzinfo=UTC)
            self.close_time = datetime(2026, 1, 1, hour + 1, 0, tzinfo=UTC)
            self.open_price = open_price
            self.high_price = high_price
            self.low_price = low_price
            self.close_price = close_price
            self.volume = volume

    return CandleStub()


def _indicator(close_price: float, offset: int) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        open_time=datetime(2026, 1, 1, offset, 0, tzinfo=UTC),
        close_time=datetime(2026, 1, 1, offset + 1, 0, tzinfo=UTC),
        close_price=close_price,
        ema_fast=close_price - 0.5,
        ema_slow=close_price - 1.0,
        ema_trend=close_price - 1.5,
        ema_by_period={100: close_price - 1.2, 200: close_price - 1.5},
        rsi=52.0 + offset,
        macd=0.1 * offset,
        macd_signal=0.08 * offset,
        macd_histogram=0.02 * offset,
        atr=1.5 + (0.1 * offset),
    )
