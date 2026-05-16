from __future__ import annotations

import argparse
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request_json(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url=url, method=method, headers=headers, data=body)
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage pinned ML models on the trading server.")
    parser.add_argument("--base-url", required=True, help="Example: http://45.15.126.248:8000")
    parser.add_argument("--action", choices=["active", "pin", "unpin", "list", "detail", "review"], required=True)
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--review-status", default="candidate")
    parser.add_argument("--review-notes", default=None)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    if args.action == "active":
        url = f"{base_url}/api/v1/ml/active-model?" + urlencode({"symbol": args.symbol, "timeframe": args.timeframe})
        print(json.dumps(request_json(url), indent=2, ensure_ascii=False))
        return

    if args.action == "list":
        url = f"{base_url}/api/v1/ml/models?" + urlencode({"symbol": args.symbol, "timeframe": args.timeframe})
        print(json.dumps(request_json(url), indent=2, ensure_ascii=False))
        return

    if args.action == "detail":
        if not args.model_id:
            raise SystemExit("--model-id is required for --action detail")
        url = f"{base_url}/api/v1/ml/model-detail?" + urlencode({"model_id": args.model_id})
        print(json.dumps(request_json(url), indent=2, ensure_ascii=False))
        return

    if args.action == "pin":
        if not args.model_id:
            raise SystemExit("--model-id is required for --action pin")
        url = f"{base_url}/api/v1/ml/pin-model"
        payload = {"symbol": args.symbol, "timeframe": args.timeframe, "model_id": args.model_id}
        print(json.dumps(request_json(url, method="POST", payload=payload), indent=2, ensure_ascii=False))
        return

    if args.action == "review":
        if not args.model_id:
            raise SystemExit("--model-id is required for --action review")
        url = f"{base_url}/api/v1/ml/review-model"
        payload = {
            "model_id": args.model_id,
            "review_status": args.review_status,
            "review_notes": args.review_notes,
        }
        print(json.dumps(request_json(url, method="POST", payload=payload), indent=2, ensure_ascii=False))
        return

    url = f"{base_url}/api/v1/ml/unpin-model?" + urlencode({"symbol": args.symbol, "timeframe": args.timeframe})
    print(json.dumps(request_json(url, method="POST"), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
