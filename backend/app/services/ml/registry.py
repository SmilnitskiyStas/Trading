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
        self.pins_path = self.models_dir / "pins.json"
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

    def update_metadata(self, model_id: str, updates: dict) -> dict:
        metadata = self.load_metadata(model_id)
        metadata.update(updates)
        self.metadata_path(model_id).write_text(
            json.dumps(metadata, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        return metadata

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

    def get_pinned_model_id(self, symbol: str, timeframe: str) -> str | None:
        pins = self._load_pins()
        return pins.get(self._pin_key(symbol=symbol, timeframe=timeframe))

    def pin_model(self, symbol: str, timeframe: str, model_id: str) -> dict:
        metadata = self.load_metadata(model_id)
        if metadata.get("symbol") != symbol or metadata.get("timeframe") != timeframe:
            raise ValueError(
                f"Model '{model_id}' belongs to {metadata.get('symbol')} {metadata.get('timeframe')}, not {symbol} {timeframe}."
            )
        pins = self._load_pins()
        pins[self._pin_key(symbol=symbol, timeframe=timeframe)] = model_id
        self._save_pins(pins)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "model_id": model_id,
            "selection_mode": "pinned",
        }

    def unpin_model(self, symbol: str, timeframe: str) -> dict:
        pins = self._load_pins()
        key = self._pin_key(symbol=symbol, timeframe=timeframe)
        removed_model_id = pins.pop(key, None)
        self._save_pins(pins)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "model_id": removed_model_id,
            "selection_mode": "latest",
        }

    def resolve_model_id(
        self,
        model_id: str | None,
        symbol: str,
        timeframe: str,
    ) -> str:
        if model_id:
            return model_id

        pinned_model_id = self.get_pinned_model_id(symbol=symbol, timeframe=timeframe)
        if pinned_model_id:
            return pinned_model_id

        models = self.list_models(symbol=symbol, timeframe=timeframe)
        if not models:
            raise FileNotFoundError(f"No trained ML models found for {symbol} {timeframe}.")
        return models[0]["model_id"]

    def resolve_active_model(self, symbol: str, timeframe: str) -> dict:
        pinned_model_id = self.get_pinned_model_id(symbol=symbol, timeframe=timeframe)
        if pinned_model_id:
            metadata = self.load_metadata(pinned_model_id)
            return {
                "model_id": pinned_model_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "selection_mode": "pinned",
                "metadata": metadata,
            }

        models = self.list_models(symbol=symbol, timeframe=timeframe)
        if not models:
            raise FileNotFoundError(f"No trained ML models found for {symbol} {timeframe}.")
        return {
            "model_id": models[0]["model_id"],
            "symbol": symbol,
            "timeframe": timeframe,
            "selection_mode": "latest",
            "metadata": models[0],
        }

    def _load_pins(self) -> dict[str, str]:
        if not self.pins_path.exists():
            return {}
        return json.loads(self.pins_path.read_text(encoding="utf-8"))

    def _save_pins(self, pins: dict[str, str]) -> None:
        self.pins_path.write_text(json.dumps(pins, ensure_ascii=True, indent=2), encoding="utf-8")

    @staticmethod
    def _pin_key(symbol: str, timeframe: str) -> str:
        return f"{symbol}::{timeframe}"

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
        return slug or "model"
