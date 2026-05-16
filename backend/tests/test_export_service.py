from datetime import UTC, datetime

from app.services.exports.service import ExportService


def test_csv_from_rows_serializes_datetime_and_none():
    content = ExportService._csv_from_rows(
        [
            {
                "name": "btc",
                "value": 1.25,
                "opened_at": datetime(2026, 5, 16, 12, 0, tzinfo=UTC),
                "note": None,
            }
        ]
    )

    assert "name,value,opened_at,note" in content
    assert "btc,1.25,2026-05-16T12:00:00+00:00," in content


def test_manifest_contains_ml_dataset_export():
    manifest = {
        "exports": {
            "ml_dataset_csv": "/api/v1/exports/ml-dataset.csv?exchange=binance&symbol=BTC/USDT&timeframe=1h"
        }
    }

    assert "/api/v1/exports/ml-dataset.csv" in manifest["exports"]["ml_dataset_csv"]
