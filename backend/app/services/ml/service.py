from datetime import UTC, datetime

import numpy as np
from fastapi import HTTPException, status
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.core.config import get_settings
from app.schemas.ml import (
    MLAdvisorySignal,
    MLActiveModelResponse,
    MLModelDetailResponse,
    MLModelReviewRequest,
    MLMetricsSummary,
    MLModelSummary,
    MLPinModelRequest,
    MLPredictRequest,
    MLPredictResponse,
    MLDatasetSplitSummary,
    MLTarget,
    MLTrainRequest,
    MLTrainResponse,
    MLWalkForwardRequest,
    MLWalkForwardResponse,
    MLWalkForwardSummary,
    MLWalkForwardWindow,
)
from app.services.indicators.service import IndicatorService
from app.services.ml.dataset import MLDatasetBuilder, MLFeatureRow
from app.services.ml.registry import MLModelRegistry


class MLService:
    def __init__(self, indicator_service: IndicatorService):
        self.indicator_service = indicator_service
        self.settings = get_settings()
        self.registry = MLModelRegistry()

    async def train(self, payload: MLTrainRequest) -> MLTrainResponse:
        resolved_target = payload.target or MLTarget(self.settings.ml_default_target)
        min_precision = payload.min_precision or self.settings.ml_default_min_precision
        min_positive_predictions = (
            payload.min_positive_predictions or self.settings.ml_default_min_positive_predictions
        )
        indicator_response = await self.indicator_service.get_indicator_snapshot(
            exchange_slug=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            limit=payload.limit,
        )
        candles = await self.indicator_service.market_data_service.list_candles(
            exchange_slug=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            limit=payload.limit,
        )
        dataset = MLDatasetBuilder.build_training_dataset(
            candles=candles,
            indicators=indicator_response.indicators,
            target=resolved_target,
            forecast_horizon_candles=payload.forecast_horizon_candles,
            min_edge_percent=payload.min_edge_percent,
        )
        self._validate_dataset(dataset.rows)

        split = MLDatasetBuilder.split_rows(
            rows=dataset.rows,
            train_ratio=self.settings.ml_train_ratio,
            validation_ratio=self.settings.ml_validation_ratio,
        )
        self._validate_split(split.train_rows, split.validation_rows, split.test_rows)

        train_x, train_y = self._rows_to_xy(split.train_rows, dataset.feature_names)
        validation_x, validation_y = self._rows_to_xy(split.validation_rows, dataset.feature_names)
        test_x, test_y = self._rows_to_xy(split.test_rows, dataset.feature_names)

        selection_result = self._select_best_model(
            train_x=train_x,
            train_y=train_y,
            validation_x=validation_x,
            validation_y=validation_y,
            min_precision=min_precision,
            min_positive_predictions=min_positive_predictions,
        )
        model = selection_result["model"]
        algorithm_name = selection_result["algorithm"]
        decision_threshold = selection_result["decision_threshold"]
        validation_metrics = selection_result["metrics"]
        test_metrics = self._evaluate(model, test_x, test_y, decision_threshold=decision_threshold)

        model_id = self.registry.create_model_id(symbol=payload.symbol, timeframe=payload.timeframe)
        dataset_path = self.registry.dataset_path(model_id)
        artifact_path = self.registry.artifact_path(model_id)
        metadata_path = self.registry.metadata_path(model_id)
        MLDatasetBuilder.export_csv(dataset_path, dataset)

        confidence_threshold = payload.confidence_threshold or self.settings.ml_default_confidence_threshold
        train_period_start = dataset.rows[0].open_time if dataset.rows else None
        train_period_end = dataset.rows[-1].close_time if dataset.rows else None
        metadata = {
            "model_id": model_id,
            "exchange": payload.exchange,
            "symbol": payload.symbol,
            "timeframe": payload.timeframe,
            "target": resolved_target.value,
            "forecast_horizon_candles": payload.forecast_horizon_candles,
            "min_edge_percent": payload.min_edge_percent,
            "min_precision": min_precision,
            "min_positive_predictions": min_positive_predictions,
            "source_bundle_label": payload.source_bundle_label,
            "algorithm": algorithm_name,
            "trained_at": datetime.now(tz=UTC).isoformat(),
            "train_period_start": train_period_start.isoformat() if train_period_start else None,
            "train_period_end": train_period_end.isoformat() if train_period_end else None,
            "dataset_rows": len(dataset.rows),
            "feature_count": len(dataset.feature_names),
            "feature_names": dataset.feature_names,
            "split": {
                "train_rows": len(split.train_rows),
                "validation_rows": len(split.validation_rows),
                "test_rows": len(split.test_rows),
            },
            "validation_metrics": validation_metrics.model_dump(),
            "test_metrics": test_metrics.model_dump(),
            "decision_threshold": decision_threshold,
            "confidence_threshold": confidence_threshold,
            "review_status": "unreviewed",
            "review_notes": None,
            "review_updated_at": None,
            "dataset_path": str(dataset_path),
            "artifact_path": str(artifact_path),
            "metadata_path": str(metadata_path),
        }
        self.registry.save_model(model_id=model_id, model=model, metadata=metadata)

        return MLTrainResponse(
            model_id=model_id,
            exchange=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            target=resolved_target,
            forecast_horizon_candles=payload.forecast_horizon_candles,
            min_edge_percent=payload.min_edge_percent,
            min_precision=min_precision,
            min_positive_predictions=min_positive_predictions,
            source_bundle_label=payload.source_bundle_label,
            algorithm=algorithm_name,
            trained_at=datetime.fromisoformat(metadata["trained_at"]),
            train_period_start=train_period_start,
            train_period_end=train_period_end,
            dataset_rows=len(dataset.rows),
            feature_count=len(dataset.feature_names),
            feature_names=dataset.feature_names,
            split=MLDatasetSplitSummary(**metadata["split"]),
            validation_metrics=validation_metrics,
            test_metrics=test_metrics,
            decision_threshold=decision_threshold,
            confidence_threshold=confidence_threshold,
            dataset_path=str(dataset_path),
            artifact_path=str(artifact_path),
            metadata_path=str(metadata_path),
        )

    async def walk_forward(self, payload: MLWalkForwardRequest) -> MLWalkForwardResponse:
        min_precision = payload.min_precision or self.settings.ml_default_min_precision
        min_positive_predictions = (
            payload.min_positive_predictions or self.settings.ml_default_min_positive_predictions
        )
        indicator_response = await self.indicator_service.get_indicator_snapshot(
            exchange_slug=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            limit=payload.limit,
        )
        candles = await self.indicator_service.market_data_service.list_candles(
            exchange_slug=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            limit=payload.limit,
        )
        dataset = MLDatasetBuilder.build_training_dataset(
            candles=candles,
            indicators=indicator_response.indicators,
            target=payload.target,
            forecast_horizon_candles=payload.forecast_horizon_candles,
            min_edge_percent=payload.min_edge_percent,
        )
        self._validate_dataset(dataset.rows)

        windows = self._build_walk_forward_windows(
            total_rows=len(dataset.rows),
            training_window_rows=payload.training_window_rows,
            validation_window_rows=payload.validation_window_rows,
            test_window_rows=payload.test_window_rows,
            step_rows=payload.step_rows,
        )
        if not windows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough ML rows for the requested walk-forward window sizes.",
            )

        responses: list[MLWalkForwardWindow] = []
        validation_metrics_rows: list[MLMetricsSummary] = []
        test_metrics_rows: list[MLMetricsSummary] = []

        for window_index, window in enumerate(windows, start=1):
            train_rows = dataset.rows[window["train_start"]:window["train_end"]]
            validation_rows = dataset.rows[window["validation_start"]:window["validation_end"]]
            test_rows = dataset.rows[window["test_start"]:window["test_end"]]
            self._validate_split(train_rows, validation_rows, test_rows)

            train_x, train_y = self._rows_to_xy(train_rows, dataset.feature_names)
            validation_x, validation_y = self._rows_to_xy(validation_rows, dataset.feature_names)
            test_x, test_y = self._rows_to_xy(test_rows, dataset.feature_names)

            selection_result = self._select_best_model(
                train_x=train_x,
                train_y=train_y,
                validation_x=validation_x,
                validation_y=validation_y,
                min_precision=min_precision,
                min_positive_predictions=min_positive_predictions,
            )
            model = selection_result["model"]
            algorithm_name = selection_result["algorithm"]
            decision_threshold = selection_result["decision_threshold"]
            validation_metrics = selection_result["metrics"]
            test_metrics = self._evaluate(model, test_x, test_y, decision_threshold=decision_threshold)

            validation_metrics_rows.append(validation_metrics)
            test_metrics_rows.append(test_metrics)
            responses.append(
                MLWalkForwardWindow(
                    window_index=window_index,
                    train_start=train_rows[0].open_time,
                    train_end=train_rows[-1].close_time,
                    validation_start=validation_rows[0].open_time,
                    validation_end=validation_rows[-1].close_time,
                    test_start=test_rows[0].open_time,
                    test_end=test_rows[-1].close_time,
                    algorithm=algorithm_name,
                    decision_threshold=decision_threshold,
                    train_rows=len(train_rows),
                    validation_rows=len(validation_rows),
                    test_rows=len(test_rows),
                    validation_metrics=validation_metrics,
                    test_metrics=test_metrics,
                )
            )

        return MLWalkForwardResponse(
            exchange=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            target=payload.target,
            forecast_horizon_candles=payload.forecast_horizon_candles,
            min_edge_percent=payload.min_edge_percent,
            min_precision=min_precision,
            min_positive_predictions=min_positive_predictions,
            confidence_threshold=payload.confidence_threshold or self.settings.ml_default_confidence_threshold,
            dataset_rows=len(dataset.rows),
            feature_count=len(dataset.feature_names),
            feature_names=dataset.feature_names,
            training_window_rows=payload.training_window_rows,
            validation_window_rows=payload.validation_window_rows,
            test_window_rows=payload.test_window_rows,
            step_rows=payload.step_rows,
            summary=self._build_walk_forward_summary(
                validation_metrics_rows=validation_metrics_rows,
                test_metrics_rows=test_metrics_rows,
            ),
            windows=responses,
        )

    async def predict(self, payload: MLPredictRequest) -> MLPredictResponse:
        try:
            resolved_model_id = self.registry.resolve_model_id(
                model_id=payload.model_id,
                symbol=payload.symbol,
                timeframe=payload.timeframe,
            )
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

        metadata = self.registry.load_metadata(resolved_model_id)
        if metadata["symbol"] != payload.symbol or metadata["timeframe"] != payload.timeframe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Model '{resolved_model_id}' was trained for {metadata['symbol']} {metadata['timeframe']}, "
                    f"not {payload.symbol} {payload.timeframe}."
                ),
            )
        indicator_response = await self.indicator_service.get_indicator_snapshot(
            exchange_slug=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            limit=payload.limit,
        )
        candles = await self.indicator_service.market_data_service.list_candles(
            exchange_slug=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            limit=payload.limit,
        )
        latest_row = MLDatasetBuilder.build_latest_feature_row(
            candles=candles,
            indicators=indicator_response.indicators,
        )
        if latest_row is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough data to build ML prediction features.",
            )

        model = self.registry.load_model(resolved_model_id)
        feature_names = metadata["feature_names"]
        row_x, _ = self._rows_to_xy([latest_row], feature_names=feature_names)
        probabilities = model.predict_proba(row_x)[0]
        probability_down = float(probabilities[0])
        probability_up = float(probabilities[1])

        confidence_threshold = payload.confidence_threshold or float(metadata["confidence_threshold"])
        decision_threshold = float(metadata.get("decision_threshold", 0.5))
        advisory_signal, confidence, passes_decision_threshold, passes_threshold = self.resolve_advisory_signal(
            probability_up=probability_up,
            decision_threshold=decision_threshold,
            threshold=confidence_threshold,
        )

        return MLPredictResponse(
            model_id=resolved_model_id,
            exchange=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            target=MLTarget(metadata["target"]),
            forecast_horizon_candles=int(metadata.get("forecast_horizon_candles", payload.forecast_horizon_candles)),
            min_edge_percent=float(metadata.get("min_edge_percent", payload.min_edge_percent)),
            min_precision=float(metadata.get("min_precision", self.settings.ml_default_min_precision)),
            min_positive_predictions=int(
                metadata.get("min_positive_predictions", self.settings.ml_default_min_positive_predictions)
            ),
            advisory_signal=advisory_signal,
            probability_up=probability_up,
            probability_down=probability_down,
            confidence=confidence,
            decision_threshold=decision_threshold,
            passes_decision_threshold=passes_decision_threshold,
            passes_confidence_threshold=passes_threshold,
            confidence_threshold=confidence_threshold,
            feature_open_time=latest_row.open_time,
            feature_close_time=latest_row.close_time,
            evaluated_at=datetime.now(tz=UTC),
            feature_values=latest_row.features,
        )

    def list_models(
        self,
        symbol: str | None = None,
        timeframe: str | None = None,
    ) -> list[MLModelSummary]:
        models = self.registry.list_models(symbol=symbol, timeframe=timeframe)
        pinned_model_id = None
        if symbol and timeframe:
            pinned_model_id = self.registry.get_pinned_model_id(symbol=symbol, timeframe=timeframe)
        return [
            MLModelSummary(
                model_id=model["model_id"],
                exchange=model["exchange"],
                symbol=model["symbol"],
                timeframe=model["timeframe"],
                target=MLTarget(model["target"]),
                forecast_horizon_candles=int(model.get("forecast_horizon_candles", 1)),
                min_edge_percent=float(model.get("min_edge_percent", 0.0)),
                min_precision=float(model.get("min_precision", self.settings.ml_default_min_precision)),
                min_positive_predictions=int(
                    model.get("min_positive_predictions", self.settings.ml_default_min_positive_predictions)
                ),
                algorithm=model["algorithm"],
                trained_at=datetime.fromisoformat(model["trained_at"]),
                train_period_start=(
                    datetime.fromisoformat(model["train_period_start"])
                    if model.get("train_period_start")
                    else None
                ),
                train_period_end=(
                    datetime.fromisoformat(model["train_period_end"])
                    if model.get("train_period_end")
                    else None
                ),
                dataset_rows=model["dataset_rows"],
                decision_threshold=float(model.get("decision_threshold", 0.5)),
                confidence_threshold=float(model["confidence_threshold"]),
                active=(
                    model["model_id"] == pinned_model_id
                    if pinned_model_id
                    else model["model_id"] == models[0]["model_id"]
                ),
                selection_mode=(
                    "pinned"
                    if pinned_model_id and model["model_id"] == pinned_model_id
                    else "latest"
                ),
                source_bundle_label=model.get("source_bundle_label"),
                review_status=model.get("review_status", "unreviewed"),
                review_notes=model.get("review_notes"),
                review_updated_at=(
                    datetime.fromisoformat(model["review_updated_at"])
                    if model.get("review_updated_at")
                    else None
                ),
            )
            for model in models
        ]

    def get_active_model(self, symbol: str, timeframe: str) -> MLActiveModelResponse:
        try:
            resolved = self.registry.resolve_active_model(symbol=symbol, timeframe=timeframe)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        metadata = resolved["metadata"]
        return MLActiveModelResponse(
            model_id=resolved["model_id"],
            symbol=symbol,
            timeframe=timeframe,
            selection_mode=resolved["selection_mode"],
            algorithm=metadata["algorithm"],
            trained_at=datetime.fromisoformat(metadata["trained_at"]),
            train_period_start=(
                datetime.fromisoformat(metadata["train_period_start"])
                if metadata.get("train_period_start")
                else None
            ),
            train_period_end=(
                datetime.fromisoformat(metadata["train_period_end"])
                if metadata.get("train_period_end")
                else None
            ),
            dataset_rows=metadata["dataset_rows"],
            confidence_threshold=float(metadata["confidence_threshold"]),
            decision_threshold=float(metadata.get("decision_threshold", 0.5)),
            review_status=metadata.get("review_status", "unreviewed"),
            review_notes=metadata.get("review_notes"),
            review_updated_at=(
                datetime.fromisoformat(metadata["review_updated_at"])
                if metadata.get("review_updated_at")
                else None
            ),
        )

    def pin_model(self, payload: MLPinModelRequest) -> MLActiveModelResponse:
        try:
            resolved = self.registry.pin_model(
                symbol=payload.symbol,
                timeframe=payload.timeframe,
                model_id=payload.model_id,
            )
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        metadata = self.registry.load_metadata(payload.model_id)
        return MLActiveModelResponse(
            model_id=resolved["model_id"],
            symbol=resolved["symbol"],
            timeframe=resolved["timeframe"],
            selection_mode=resolved["selection_mode"],
            algorithm=metadata["algorithm"],
            trained_at=datetime.fromisoformat(metadata["trained_at"]),
            train_period_start=(
                datetime.fromisoformat(metadata["train_period_start"])
                if metadata.get("train_period_start")
                else None
            ),
            train_period_end=(
                datetime.fromisoformat(metadata["train_period_end"])
                if metadata.get("train_period_end")
                else None
            ),
            dataset_rows=metadata["dataset_rows"],
            confidence_threshold=float(metadata["confidence_threshold"]),
            decision_threshold=float(metadata.get("decision_threshold", 0.5)),
            review_status=metadata.get("review_status", "unreviewed"),
            review_notes=metadata.get("review_notes"),
            review_updated_at=(
                datetime.fromisoformat(metadata["review_updated_at"])
                if metadata.get("review_updated_at")
                else None
            ),
        )

    def unpin_model(self, symbol: str, timeframe: str) -> MLActiveModelResponse:
        self.registry.unpin_model(symbol=symbol, timeframe=timeframe)
        return self.get_active_model(symbol=symbol, timeframe=timeframe)

    def get_model_detail(self, model_id: str) -> MLModelDetailResponse:
        try:
            metadata = self.registry.load_metadata(model_id)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        return MLModelDetailResponse(
            model_id=metadata["model_id"],
            exchange=metadata["exchange"],
            symbol=metadata["symbol"],
            timeframe=metadata["timeframe"],
            target=MLTarget(metadata["target"]),
            algorithm=metadata["algorithm"],
            trained_at=datetime.fromisoformat(metadata["trained_at"]),
            dataset_rows=metadata["dataset_rows"],
            feature_count=metadata.get("feature_count"),
            forecast_horizon_candles=metadata.get("forecast_horizon_candles"),
            min_edge_percent=metadata.get("min_edge_percent"),
            min_precision=metadata.get("min_precision"),
            min_positive_predictions=metadata.get("min_positive_predictions"),
            source_bundle_label=metadata.get("source_bundle_label"),
            train_period_start=(
                datetime.fromisoformat(metadata["train_period_start"])
                if metadata.get("train_period_start")
                else None
            ),
            train_period_end=(
                datetime.fromisoformat(metadata["train_period_end"])
                if metadata.get("train_period_end")
                else None
            ),
            decision_threshold=metadata.get("decision_threshold"),
            confidence_threshold=metadata.get("confidence_threshold"),
            validation_metrics=metadata.get("validation_metrics"),
            test_metrics=metadata.get("test_metrics"),
            review_status=metadata.get("review_status", "unreviewed"),
            review_notes=metadata.get("review_notes"),
            review_updated_at=(
                datetime.fromisoformat(metadata["review_updated_at"])
                if metadata.get("review_updated_at")
                else None
            ),
        )

    def review_model(self, payload: MLModelReviewRequest) -> MLModelDetailResponse:
        try:
            metadata = self.registry.update_metadata(
                payload.model_id,
                {
                    "review_status": payload.review_status,
                    "review_notes": payload.review_notes,
                    "review_updated_at": datetime.now(tz=UTC).isoformat(),
                },
            )
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        return self.get_model_detail(metadata["model_id"])

    @staticmethod
    def resolve_advisory_signal(
        probability_up: float,
        decision_threshold: float,
        threshold: float,
    ) -> tuple[MLAdvisorySignal, float, bool, bool]:
        probability_down = 1.0 - probability_up
        passes_decision_threshold = probability_up >= decision_threshold
        if passes_decision_threshold:
            confidence = probability_up
            passes_threshold = confidence >= threshold
            if not passes_threshold:
                return MLAdvisorySignal.HOLD, confidence, True, False
            return MLAdvisorySignal.UP, confidence, True, True

        confidence = probability_down
        passes_threshold = confidence >= threshold
        if not passes_threshold:
            return MLAdvisorySignal.HOLD, confidence, False, False
        return MLAdvisorySignal.DOWN, confidence, False, True

    @staticmethod
    def _candidate_models() -> list[tuple[str, object]]:
        return [
            (
                "logistic_regression_v1_1",
                Pipeline(
                    steps=[
                        ("scaler", StandardScaler()),
                        (
                            "classifier",
                            LogisticRegression(
                                max_iter=1000,
                                random_state=42,
                                class_weight="balanced",
                            ),
                        ),
                    ]
                ),
            ),
            (
                "random_forest_v1_1",
                RandomForestClassifier(
                    n_estimators=250,
                    max_depth=6,
                    min_samples_leaf=8,
                    random_state=42,
                    class_weight="balanced_subsample",
                ),
            ),
            (
                "hist_gradient_boosting_v1_1",
                HistGradientBoostingClassifier(
                    max_iter=200,
                    learning_rate=0.05,
                    max_depth=5,
                    min_samples_leaf=20,
                    random_state=42,
                ),
            ),
        ]

    def _select_best_model(
        self,
        train_x: np.ndarray,
        train_y: np.ndarray,
        validation_x: np.ndarray,
        validation_y: np.ndarray,
        min_precision: float,
        min_positive_predictions: int,
    ) -> dict:
        best_result: dict | None = None
        for algorithm_name, candidate in self._candidate_models():
            candidate.fit(train_x, train_y)
            probabilities = candidate.predict_proba(validation_x)[:, 1]
            decision_threshold = self._find_best_decision_threshold(
                probabilities,
                validation_y,
                min_precision=min_precision,
                min_positive_predictions=min_positive_predictions,
            )
            metrics = self._evaluate(
                candidate,
                validation_x,
                validation_y,
                decision_threshold=decision_threshold,
            )
            score = self._model_selection_score(metrics)
            if best_result is None or score > best_result["score"]:
                best_result = {
                    "algorithm": algorithm_name,
                    "model": candidate,
                    "decision_threshold": decision_threshold,
                    "metrics": metrics,
                    "score": score,
                }

        if best_result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ML model selection did not produce a valid candidate.",
            )
        return best_result

    @staticmethod
    def _model_selection_score(metrics: MLMetricsSummary) -> float:
        roc_auc_score_value = metrics.roc_auc or 0.0
        return (metrics.f1_score * 0.45) + (metrics.precision * 0.20) + (metrics.recall * 0.10) + (roc_auc_score_value * 0.25)

    @staticmethod
    def _build_walk_forward_windows(
        total_rows: int,
        training_window_rows: int,
        validation_window_rows: int,
        test_window_rows: int,
        step_rows: int,
    ) -> list[dict[str, int]]:
        windows: list[dict[str, int]] = []
        cursor = 0
        required_span = training_window_rows + validation_window_rows + test_window_rows
        while cursor + required_span <= total_rows:
            windows.append(
                {
                    "train_start": cursor,
                    "train_end": cursor + training_window_rows,
                    "validation_start": cursor + training_window_rows,
                    "validation_end": cursor + training_window_rows + validation_window_rows,
                    "test_start": cursor + training_window_rows + validation_window_rows,
                    "test_end": cursor + required_span,
                }
            )
            cursor += step_rows
        return windows

    @staticmethod
    def _build_walk_forward_summary(
        validation_metrics_rows: list[MLMetricsSummary],
        test_metrics_rows: list[MLMetricsSummary],
    ) -> MLWalkForwardSummary:
        def average(values: list[float]) -> float:
            return float(sum(values) / len(values)) if values else 0.0

        def average_optional(values: list[float | None]) -> float | None:
            filtered = [value for value in values if value is not None]
            return float(sum(filtered) / len(filtered)) if filtered else None

        return MLWalkForwardSummary(
            windows=len(test_metrics_rows),
            average_validation_accuracy=average([item.accuracy for item in validation_metrics_rows]),
            average_validation_roc_auc=average_optional([item.roc_auc for item in validation_metrics_rows]),
            average_test_accuracy=average([item.accuracy for item in test_metrics_rows]),
            average_test_precision=average([item.precision for item in test_metrics_rows]),
            average_test_recall=average([item.recall for item in test_metrics_rows]),
            average_test_f1=average([item.f1_score for item in test_metrics_rows]),
            average_test_roc_auc=average_optional([item.roc_auc for item in test_metrics_rows]),
        )

    @staticmethod
    def _rows_to_xy(rows: list[MLFeatureRow], feature_names: list[str]) -> tuple[np.ndarray, np.ndarray]:
        features = [[row.features[name] for name in feature_names] for row in rows]
        targets = [row.target_up for row in rows]
        return np.array(features, dtype=float), np.array(targets, dtype=int)

    @staticmethod
    def _evaluate(
        model: Pipeline,
        features: np.ndarray,
        targets: np.ndarray,
        decision_threshold: float = 0.5,
    ) -> MLMetricsSummary:
        probabilities = model.predict_proba(features)[:, 1]
        predictions = (probabilities >= decision_threshold).astype(int)
        unique_targets = np.unique(targets)
        roc_auc = float(roc_auc_score(targets, probabilities)) if len(unique_targets) > 1 else None
        return MLMetricsSummary(
            accuracy=float(accuracy_score(targets, predictions)),
            precision=float(precision_score(targets, predictions, zero_division=0)),
            recall=float(recall_score(targets, predictions, zero_division=0)),
            f1_score=float(f1_score(targets, predictions, zero_division=0)),
            positive_rate=float(np.mean(targets)),
            roc_auc=roc_auc,
        )

    @staticmethod
    def _find_best_decision_threshold(
        probabilities: np.ndarray,
        targets: np.ndarray,
        min_precision: float = 0.0,
        min_positive_predictions: int = 0,
    ) -> float:
        return MLService._find_best_decision_threshold_with_floor(
            probabilities=probabilities,
            targets=targets,
            min_precision=min_precision,
            min_positive_predictions=min_positive_predictions,
        )

    @staticmethod
    def _find_best_decision_threshold_with_floor(
        probabilities: np.ndarray,
        targets: np.ndarray,
        min_precision: float,
        min_positive_predictions: int = 0,
    ) -> float:
        best_threshold = 0.5
        best_score = float("-inf")
        fallback_threshold = 0.5
        fallback_score = float("-inf")

        for raw_threshold in np.arange(0.30, 0.76, 0.02):
            threshold = float(round(raw_threshold, 2))
            predictions = (probabilities >= threshold).astype(int)
            predicted_positive_count = int(np.sum(predictions))
            precision = float(precision_score(targets, predictions, zero_division=0))
            recall = float(recall_score(targets, predictions, zero_division=0))
            f1 = float(f1_score(targets, predictions, zero_division=0))
            score = (f1 * 0.45) + (precision * 0.40) + (recall * 0.15)

            if score > fallback_score:
                fallback_score = score
                fallback_threshold = threshold

            if precision < min_precision:
                continue
            if predicted_positive_count < min_positive_predictions:
                continue

            if score > best_score:
                best_score = score
                best_threshold = threshold

        if best_score == float("-inf"):
            return fallback_threshold
        return best_threshold

    def _validate_dataset(self, rows: list[MLFeatureRow]) -> None:
        if len(rows) < self.settings.ml_min_rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Not enough ML rows to train. Need at least {self.settings.ml_min_rows}, "
                    f"got {len(rows)}."
                ),
            )

    @staticmethod
    def _validate_split(train_rows: list[MLFeatureRow], validation_rows: list[MLFeatureRow], test_rows: list[MLFeatureRow]) -> None:
        if not train_rows or not validation_rows or not test_rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ML split produced an empty train, validation, or test segment.",
            )
        train_classes = {row.target_up for row in train_rows}
        if len(train_classes) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ML train split must contain both up and down target classes.",
            )
