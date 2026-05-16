# Crypto Trading Research Bot

Foundation scaffold for a crypto trading research platform with a safety-first architecture:

- FastAPI backend
- PostgreSQL for persistent storage
- Redis for cache and short-lived state
- Docker Compose for local development
- Health checks and centralized configuration

## Current phase

This repository is currently in the MVP research stage. The current milestone includes:

- backend service skeleton
- environment-driven configuration
- Docker setup for local services
- starter Alembic layout
- `/health` and `/api/v1/health` endpoints
- initial market data sync/read flow for OHLCV candles
- first rule-based strategy plus risk evaluation flow
- paper trading, event logging, and Telegram notification plumbing
- symbol-based strategy routing:
  - `BTC/USDT -> rsi_ema_trend_v2`
  - `ETH/USDT -> rsi_ema_trend_multi_v1`
- background automation runner for scheduled sync plus paper cycles
- built-in dashboard at `/dashboard`
- ML v1 training and prediction API with saved local model artifacts

Real trading is intentionally out of scope for MVP. The system is being built for research, backtesting, and paper trading first.

## Quick start

1. Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

2. Start the stack:

```powershell
docker compose up --build
```

3. Open:

- API docs: `http://localhost:8000/docs`
- Health endpoint: `http://localhost:8000/health`
- Dashboard: `http://localhost:8000/dashboard`

## Server deployment

For a server, use the dedicated compose file instead of the local development one.

Why:

- no `--reload`
- no bind-mount of the source code into the container
- PostgreSQL and Redis stay private inside Docker
- Alembic migrations run automatically before backend startup
- trained ML artifacts are stored in Docker volumes and survive backend rebuilds

Recommended deployment flow:

1. Copy the project to the server.
2. Create a real `.env` from `.env.example`.
3. Set at least:
   - `APP_ENV=server`
   - `BACKEND_RELOAD=false`
   - `TELEGRAM_ENABLED=true` if you want live alerts
   - real `TELEGRAM_BOT_TOKEN`
   - real `TELEGRAM_CHAT_ID`
4. Start:

```powershell
docker compose -f docker-compose.server.yml up -d --build
```

5. Open:

- `http://SERVER_IP:8000/health`
- `http://SERVER_IP:8000/dashboard`
- `http://SERVER_IP:8000/docs`

Useful server commands:

```powershell
docker compose -f docker-compose.server.yml ps
docker compose -f docker-compose.server.yml logs -f backend
docker compose -f docker-compose.server.yml restart backend
docker compose -f docker-compose.server.yml down
```

Notes:

- On a public server, open only port `8000` in the firewall if you plan to access the dashboard directly.
- Do not expose PostgreSQL or Redis to the internet.
- For a cleaner public setup, put Nginx or Caddy in front later and serve the app through a domain and HTTPS.
- Server ML storage now lives in Docker volumes mounted to `/app/ml/models` and `/app/ml/datasets`.

## Automation

The backend now starts an internal automation loop on startup. Each cycle:

1. Syncs OHLCV for all configured MVP symbols and timeframes.
2. Runs paper-trading execution for configured execution timeframes.
3. Uses symbol-specific routing so `BTC/USDT` uses `rsi_ema_trend_v2` and `ETH/USDT` uses `rsi_ema_trend_multi_v1`.

Useful endpoints:

- `GET /api/v1/automation/status`
- `POST /api/v1/automation/run-once`
- `POST /api/v1/automation/pause`
- `POST /api/v1/automation/resume`
- `POST /api/v1/automation/stop`
- `GET /api/v1/automation/kill-switch`
- `POST /api/v1/automation/kill-switch/enable`
- `POST /api/v1/automation/kill-switch/disable`
- `GET /api/v1/paper-trading/account?account_name=paper-main`
- `GET /api/v1/paper-trading/test-status?account_name=paper-main`
- `GET /api/v1/paper-trading/performance?account_name=paper-main`
- `GET /api/v1/paper-trading/performance/by-day?account_name=paper-main`
- `GET /api/v1/paper-trading/performance/by-symbol?account_name=paper-main`
- `GET /api/v1/reports/daily/preview?account_name=paper-main`
- `POST /api/v1/reports/daily/send?account_name=paper-main&force=true`
- `GET /api/v1/events?limit=20`

Relevant environment settings:

- `AUTOMATION_ENABLED`
- `AUTOMATION_ACCOUNT_NAME`
- `AUTOMATION_LOOP_INTERVAL_SECONDS`
- `AUTOMATION_EXECUTION_TIMEFRAMES`
- `STRATEGY_SYMBOL_OVERRIDES`
- `DAILY_REPORT_ENABLED`
- `DAILY_REPORT_ACCOUNT_NAME`
- `DAILY_REPORT_TIMEZONE`
- `DAILY_REPORT_TIME_LOCAL`
- `ML_MODELS_DIR`
- `ML_DATASETS_DIR`
- `ML_DEFAULT_CONFIDENCE_THRESHOLD`
- `ML_DEFAULT_MIN_PRECISION`
- `ML_DEFAULT_MIN_POSITIVE_PREDICTIONS`
- `ML_TRAIN_RATIO`
- `ML_VALIDATION_RATIO`
- `ML_TEST_RATIO`
- `ML_MIN_ROWS`
- `ML_RISK_FILTER_ENABLED`
- `ML_RISK_FILTER_REQUIRE_MODEL`
- `ML_RISK_FILTER_CONFIDENCE_THRESHOLD`

## ML v1

The first ML layer is designed as a research-only confidence model. It does not place trades and does not bypass the risk engine.

Current behavior:

- builds a feature dataset from stored candles plus indicators
- uses a chronological train/validation/test split
- expands the dataset with richer lag, momentum, and regime features
- compares multiple candidate classifiers on the validation split
- supports multiple targets, including `future_edge_long`
- in `v1.2`, can train on a forward edge target using:
  - `forecast_horizon_candles`
  - `min_edge_percent`
- in `v1.3.2`, can tune `decision_threshold` with both a minimum precision floor and a minimum count of positive validation signals
- saves the dataset snapshot and model artifact locally
- provides prediction probabilities and a confidence threshold gate

Useful endpoints:

- `POST /api/v1/ml/train`
- `POST /api/v1/ml/walk-forward`
- `POST /api/v1/ml/predict`
- `GET /api/v1/ml/models`
- `GET /api/v1/ml/active-model?symbol=BTC/USDT&timeframe=1h`
- `GET /api/v1/ml/model-detail?model_id=btc_usdt_1h_20260516T120000Z`
- `POST /api/v1/ml/pin-model`
- `POST /api/v1/ml/unpin-model?symbol=BTC/USDT&timeframe=1h`
- `POST /api/v1/ml/review-model`

## Data Export

While the server is collecting runtime data, you can now export it directly for local analysis and retraining.

Useful endpoints:

- `GET /api/v1/exports/manifest`
- `GET /api/v1/exports/candles.csv?exchange=binance&symbol=BTC/USDT&timeframe=1h&limit=3000`
- `GET /api/v1/exports/paper-trades.csv?account_name=paper-main&limit=5000`
- `GET /api/v1/exports/events.csv?limit=5000`
- `GET /api/v1/exports/daily-reports.csv?account_name=paper-main&limit=365`
- `GET /api/v1/exports/ml-dataset.csv?exchange=binance&symbol=BTC/USDT&timeframe=1h&limit=3000&target=future_edge_long&forecast_horizon_candles=3&min_edge_percent=0.4`

Practical use:

- export raw candles when you want to rebuild research datasets locally
- export `ml-dataset.csv` when you want the server to produce the feature snapshot for local training
- export paper trades, events, and daily reports to compare model versions against live paper behavior

Helper scripts:

- [backend/scripts/fetch_runtime_exports.py](C:/Users/stass/source/Trading/backend/scripts/fetch_runtime_exports.py)
- [backend/scripts/manage_remote_model_pin.py](C:/Users/stass/source/Trading/backend/scripts/manage_remote_model_pin.py)
- [docs/server_ml_workflow.md](C:/Users/stass/source/Trading/docs/server_ml_workflow.md)

Backup and restore:

- [ops/server_backup.sh](C:/Users/stass/source/Trading/ops/server_backup.sh)
- [ops/server_restore.sh](C:/Users/stass/source/Trading/ops/server_restore.sh)
- [docs/server_backup_restore.md](C:/Users/stass/source/Trading/docs/server_backup_restore.md)

Optional ML risk gate:

- when `ML_RISK_FILTER_ENABLED=true`, the risk engine asks the latest trained model to confirm new long entries
- if the ML advisory is not `UP` with sufficient confidence, the entry is blocked before paper execution
- if `ML_RISK_FILTER_REQUIRE_MODEL=true`, missing ML models also block new entries
- `POST /api/v1/risk/evaluate` now includes `ml_filter` details in the response when the ML gate is enabled

Model deployment workflow:

- train locally
- copy `.joblib` and `.json` artifacts to the server ML storage
- use `GET /api/v1/ml/models` to confirm the model is visible
- use `GET /api/v1/ml/model-detail` to inspect full metadata for one model
- use `POST /api/v1/ml/review-model` to attach a verdict and notes
- use `POST /api/v1/ml/pin-model` to make one exact model active for a symbol and timeframe
- use `POST /api/v1/ml/unpin-model` to fall back to the latest available model again

## Safety Controls

The emergency kill switch blocks new entries through the risk engine, including:

- manual risk evaluation
- automation-driven paper cycles
- paper trading entry flow

It does not interfere with:

- health checks
- market data sync
- dashboard access
- exit handling for already open positions

## Daily Report

The system now supports a Telegram daily report with:

- health status
- automation mode and loop status
- kill-switch status
- account balance and realized return
- trade counts and profit factor
- per-symbol performance summary
- recent operational events

Reports can be:

- previewed through the API
- sent manually on demand
- sent automatically once per day after the configured local report time

## Paper Test Mode

To decide whether the bot is working in plus or minus, use the paper-test view first rather than judging one signal at a time.

- dashboard: `http://localhost:8000/dashboard`
- API summary: `GET /api/v1/paper-trading/test-status?account_name=paper-main`

The test-status endpoint now shows:

- current phase such as `BOOTSTRAPPING`, `COLLECTING_DATA`, or `EVALUATING`
- whether there is enough closed-trade history to judge performance
- current realized PnL and realized return
- the latest closed-trade result
- a plain-English summary of what the current state means

## Repository layout

```text
backend/
  app/
    api/
    core/
    db/
    models/
    services/
    main.py
  alembic/
  tests/
  Dockerfile
  requirements.txt
docker-compose.yml
.env.example
README.md
PROJECT_PROMPT.md
```

## Next implementation steps

1. Add richer analytics and trade journal summaries.
2. Add emergency stop and pause controls for automation.
3. Add performance widgets and backtest comparison blocks to the dashboard.
4. Add dedicated tests for automation runner behavior.
