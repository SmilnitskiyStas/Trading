from datetime import UTC, datetime
from pathlib import Path
import json
import re

import joblib

from app.core.config import get_settings


class MLModelRegistry:
    def __init__(self):
        self.settings = get_settings()
        self.models_dir = Path(self.settings.ml_models_dir)
        self.datasets_dir = Path(self.settings.ml_datasets_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)

    def create_model_id(self, symbol: str, timeframe: str) -> str:
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        return f"{self._slugify(symbol)}_{timeframe}_{timestamp}"

    def artifact_path(self, model_id: str) -> Path:
        return self.models_dir / f"{model_id}.joblib"

    def metadata_path(self, model_id: str) -> Path:
        return self.models_dir / f"{model_id}.json"

    def dataset_path(self, model_id: str) -> Path:
        return self.datasets_dir / f"{model_id}.csv"

    def save_model(self, model_id: str, model, metadata: dict) -> None:
        artifact_path = self.artifact_path(model_id)
        metadata_path = self.metadata_path(model_id)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, artifact_path)
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=True, indent=2), encoding="utf-8")

    def load_model(self, model_id: str):
        return joblib.load(self.artifact_path(model_id))

    def load_metadata(self, model_id: str) -> dict:
        return json.loads(self.metadata_path(model_id).read_text(encoding="utf-8"))

    def list_models(
        self,
        symbol: str | None = None,
        timeframe: str | None = None,
    ) -> list[dict]:
        entries: list[dict] = []
        for metadata_file in sorted(self.models_dir.glob("*.json"), reverse=True):
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            if symbol and metadata.get("symbol") != symbol:
                continue
            if timeframe and metadata.get("timeframe") != timeframe:
                continue
            entries.append(metadata)
        return entries

    def resolve_model_id(
        self,
        model_id: str | None,
        symbol: str,
        timeframe: str,
    ) -> str:
        if model_id:
            return model_id

        models = self.list_models(symbol=symbol, timeframe=timeframe)
        if not models:
            raise FileNotFoundError(f"No trained ML models found for {symbol} {timeframe}.")
        return models[0]["model_id"]

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
        return slug or "model"
