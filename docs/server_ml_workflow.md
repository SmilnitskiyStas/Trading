# Server ML Workflow

This runbook is for the operating model where:

- the server runs the bot continuously
- the server collects market data and paper-trading results
- local training happens on a stronger machine
- trained models are copied back to the server and pinned through the API

## 1. Export runtime data from the server

Example:

```bash
python backend/scripts/fetch_runtime_exports.py \
  --base-url http://45.15.126.248:8000 \
  --exchange binance \
  --symbol BTC/USDT \
  --timeframe 1h \
  --account-name paper-main \
  --limit 3000 \
  --out-dir runtime_exports
```

This downloads:

- `manifest.json`
- raw candles
- paper trades
- system events
- daily report history
- a ready-made `ml_dataset.csv`

## 2. Train locally

Use the exported data for research and model training on the local machine.

## 3. Copy trained artifacts to the server

Example:

```bash
scp backend/ml/models/btc_usdt_1h_20260516T120000Z.joblib user@SERVER_IP:/tmp/
scp backend/ml/models/btc_usdt_1h_20260516T120000Z.json user@SERVER_IP:/tmp/
```

Then on the server:

```bash
docker cp /tmp/btc_usdt_1h_20260516T120000Z.joblib trading-backend:/app/ml/models/
docker cp /tmp/btc_usdt_1h_20260516T120000Z.json trading-backend:/app/ml/models/
```

Optional dataset artifact:

```bash
scp backend/ml/datasets/btc_usdt_1h_20260516T120000Z.csv user@SERVER_IP:/tmp/
docker cp /tmp/btc_usdt_1h_20260516T120000Z.csv trading-backend:/app/ml/datasets/
```

## 4. Check visible models on the server

```bash
python backend/scripts/manage_remote_model_pin.py \
  --base-url http://45.15.126.248:8000 \
  --action list \
  --symbol BTC/USDT \
  --timeframe 1h
```

## 5. Pin the exact model you want active

```bash
python backend/scripts/manage_remote_model_pin.py \
  --base-url http://45.15.126.248:8000 \
  --action pin \
  --symbol BTC/USDT \
  --timeframe 1h \
  --model-id btc_usdt_1h_20260516T120000Z
```

Check the active model:

```bash
python backend/scripts/manage_remote_model_pin.py \
  --base-url http://45.15.126.248:8000 \
  --action active \
  --symbol BTC/USDT \
  --timeframe 1h
```

## 5.1. Review and annotate the model

Inspect one model:

```bash
python backend/scripts/manage_remote_model_pin.py \
  --base-url http://45.15.126.248:8000 \
  --action detail \
  --model-id btc_usdt_1h_20260516T120000Z
```

Attach a verdict:

```bash
python backend/scripts/manage_remote_model_pin.py \
  --base-url http://45.15.126.248:8000 \
  --action review \
  --model-id btc_usdt_1h_20260516T120000Z \
  --review-status approved_for_paper_gate \
  --review-notes "Passed local walk-forward and is ready for BTC 1h paper filtering."
```

## 6. Unpin if you want to fall back to the latest model

```bash
python backend/scripts/manage_remote_model_pin.py \
  --base-url http://45.15.126.248:8000 \
  --action unpin \
  --symbol BTC/USDT \
  --timeframe 1h
```
