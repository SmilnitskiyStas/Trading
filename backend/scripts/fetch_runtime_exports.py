from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


def fetch_bytes(url: str) -> bytes:
    with urlopen(url) as response:
        return response.read()


def write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download runtime export bundle from the trading server.")
    parser.add_argument("--base-url", required=True, help="Example: http://45.15.126.248:8000")
    parser.add_argument("--exchange", default="binance")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--account-name", default="paper-main")
    parser.add_argument("--limit", type=int, default=3000)
    parser.add_argument("--target", default="future_edge_long")
    parser.add_argument("--forecast-horizon-candles", type=int, default=3)
    parser.add_argument("--min-edge-percent", type=float, default=0.4)
    parser.add_argument("--out-dir", default="runtime_exports")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    out_dir = Path(args.out_dir)
    symbol_slug = args.symbol.replace("/", "_")

    downloads = {
        "manifest.json": f"{base_url}/api/v1/exports/manifest",
        f"candles_{symbol_slug}_{args.timeframe}.csv": (
            f"{base_url}/api/v1/exports/candles.csv?"
            + urlencode(
                {
                    "exchange": args.exchange,
                    "symbol": args.symbol,
                    "timeframe": args.timeframe,
                    "limit": args.limit,
                }
            )
        ),
        f"paper_trades_{args.account_name}.csv": (
            f"{base_url}/api/v1/exports/paper-trades.csv?"
            + urlencode({"account_name": args.account_name, "limit": 5000})
        ),
        "events.csv": f"{base_url}/api/v1/exports/events.csv?" + urlencode({"limit": 5000}),
        f"daily_reports_{args.account_name}.csv": (
            f"{base_url}/api/v1/exports/daily-reports.csv?"
            + urlencode({"account_name": args.account_name, "limit": 365})
        ),
        f"ml_dataset_{symbol_slug}_{args.timeframe}.csv": (
            f"{base_url}/api/v1/exports/ml-dataset.csv?"
            + urlencode(
                {
                    "exchange": args.exchange,
                    "symbol": args.symbol,
                    "timeframe": args.timeframe,
                    "limit": args.limit,
                    "target": args.target,
                    "forecast_horizon_candles": args.forecast_horizon_candles,
                    "min_edge_percent": args.min_edge_percent,
                }
            )
        ),
    }

    for filename, url in downloads.items():
        destination = out_dir / filename
        print(f"Downloading {url}")
        write_file(destination, fetch_bytes(url))
        print(f"Saved {destination}")


if __name__ == "__main__":
    main()
