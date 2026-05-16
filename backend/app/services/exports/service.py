from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import csv
import io
import json

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.daily_report_history_repository import DailyReportHistoryRepository
from app.repositories.exchange_repository import ExchangeRepository
from app.repositories.paper_account_repository import PaperAccountRepository
from app.repositories.paper_trade_repository import PaperTradeRepository
from app.repositories.system_event_repository import SystemEventRepository
from app.repositories.trading_pair_repository import TradingPairRepository
from app.schemas.ml import MLTarget
from app.services.indicators.service import IndicatorService
from app.services.market_data.service import MarketDataService
from app.services.ml.dataset import MLDatasetBuilder


class ExportService:
    def __init__(
        self,
        session: AsyncSession,
        market_data_service: MarketDataService,
        indicator_service: IndicatorService,
    ):
        self.session = session
        self.market_data_service = market_data_service
        self.indicator_service = indicator_service
        self.exchange_repository = ExchangeRepository(session)
        self.trading_pair_repository = TradingPairRepository(session)
        self.paper_account_repository = PaperAccountRepository(session)
        self.paper_trade_repository = PaperTradeRepository(session)
        self.system_event_repository = SystemEventRepository(session)
        self.daily_report_history_repository = DailyReportHistoryRepository(session)

    async def build_manifest(self) -> dict:
        generated_at = datetime.now(tz=UTC).isoformat()
        return {
            "generated_at": generated_at,
            "exports": {
                "candles_csv": "/api/v1/exports/candles.csv?exchange=binance&symbol=BTC/USDT&timeframe=1h&limit=3000",
                "paper_trades_csv": "/api/v1/exports/paper-trades.csv?account_name=paper-main&limit=5000",
                "events_csv": "/api/v1/exports/events.csv?limit=5000",
                "daily_reports_csv": "/api/v1/exports/daily-reports.csv?account_name=paper-main&limit=365",
                "ml_dataset_csv": (
                    "/api/v1/exports/ml-dataset.csv?exchange=binance&symbol=BTC/USDT&timeframe=1h"
                    "&limit=3000&target=future_edge_long&forecast_horizon_candles=3&min_edge_percent=0.4"
                ),
            },
            "notes": [
                "Use candles export for raw OHLCV history from the server.",
                "Use ml-dataset export when you want a ready-made feature snapshot for local ML training.",
                "Paper trades, events, and daily reports help align model training with live paper performance.",
            ],
        }

    async def export_candles_csv(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> tuple[str, str]:
        candles = await self.market_data_service.list_candles(
            exchange_slug=exchange,
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
        )
        rows = [
            {
                "exchange": exchange,
                "symbol": symbol,
                "timeframe": timeframe,
                "open_time": candle.open_time,
                "close_time": candle.close_time,
                "open_price": candle.open_price,
                "high_price": candle.high_price,
                "low_price": candle.low_price,
                "close_price": candle.close_price,
                "volume": candle.volume,
            }
            for candle in candles
        ]
        filename = f"candles_{self._slugify(exchange)}_{self._slugify(symbol)}_{timeframe}_{len(rows)}.csv"
        return filename, self._csv_from_rows(rows)

    async def export_paper_trades_csv(
        self,
        account_name: str,
        limit: int,
    ) -> tuple[str, str]:
        account = await self.paper_account_repository.get_or_create(
            name=account_name,
            initial_balance=Decimal("1000"),
        )
        trades = await self.paper_trade_repository.list_recent(account.id, limit)
        symbol_map = await self._symbol_map_for_trade_ids(trades)
        rows = [
            {
                "account_name": account_name,
                "trade_id": trade.id,
                "symbol": symbol_map.get(trade.trading_pair_id, f"pair:{trade.trading_pair_id}"),
                "strategy_name": trade.strategy_name,
                "timeframe": trade.timeframe,
                "status": trade.status,
                "side": trade.side,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "stop_loss_price": trade.stop_loss_price,
                "take_profit_price": trade.take_profit_price,
                "position_size": trade.position_size,
                "fees_paid": trade.fees_paid,
                "realized_pnl": trade.realized_pnl,
                "exit_reason": trade.exit_reason,
                "opened_at": trade.opened_at,
                "closed_at": trade.closed_at,
                "created_at": trade.created_at,
                "updated_at": trade.updated_at,
            }
            for trade in trades
        ]
        filename = f"paper_trades_{self._slugify(account_name)}_{len(rows)}.csv"
        return filename, self._csv_from_rows(rows)

    async def export_events_csv(self, limit: int) -> tuple[str, str]:
        events = await self.system_event_repository.list_recent(limit=limit)
        rows = [
            {
                "event_id": event.id,
                "account_id": event.account_id,
                "paper_trade_id": event.paper_trade_id,
                "event_type": event.event_type,
                "level": event.level,
                "message": event.message,
                "payload_json": json.dumps(event.payload or {}, ensure_ascii=True),
                "created_at": event.created_at,
                "updated_at": event.updated_at,
            }
            for event in events
        ]
        filename = f"system_events_{len(rows)}.csv"
        return filename, self._csv_from_rows(rows)

    async def export_daily_reports_csv(
        self,
        account_name: str | None,
        limit: int,
    ) -> tuple[str, str]:
        reports = await self.daily_report_history_repository.list_recent(limit=limit, account_name=account_name)
        rows = [
            {
                "report_id": report.id,
                "account_name": report.account_name,
                "report_date": report.report_date,
                "timezone": report.timezone,
                "trigger_type": report.trigger_type,
                "status": report.status,
                "detail": report.detail,
                "message": report.message,
                "created_at": report.created_at,
                "updated_at": report.updated_at,
            }
            for report in reports
        ]
        base_name = self._slugify(account_name or "all_accounts")
        filename = f"daily_reports_{base_name}_{len(rows)}.csv"
        return filename, self._csv_from_rows(rows)

    async def export_ml_dataset_csv(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int,
        target: MLTarget,
        forecast_horizon_candles: int,
        min_edge_percent: float,
    ) -> tuple[str, str]:
        indicator_response = await self.indicator_service.get_indicator_snapshot(
            exchange_slug=exchange,
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
        )
        candles = await self.market_data_service.list_candles(
            exchange_slug=exchange,
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
        )
        dataset = MLDatasetBuilder.build_training_dataset(
            candles=candles,
            indicators=indicator_response.indicators,
            target=target,
            forecast_horizon_candles=forecast_horizon_candles,
            min_edge_percent=min_edge_percent,
        )
        if not dataset.rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough data to build an ML dataset export for the requested window.",
            )

        rows = [
            {
                "exchange": exchange,
                "symbol": symbol,
                "timeframe": timeframe,
                "target": target.value,
                "forecast_horizon_candles": forecast_horizon_candles,
                "min_edge_percent": min_edge_percent,
                "open_time": row.open_time,
                "close_time": row.close_time,
                **row.features,
                "target_up": row.target_up,
            }
            for row in dataset.rows
        ]
        filename = (
            f"ml_dataset_{self._slugify(exchange)}_{self._slugify(symbol)}_{timeframe}_"
            f"{target.value}_{len(rows)}.csv"
        )
        return filename, self._csv_from_rows(rows)

    async def _symbol_map_for_trade_ids(self, trades) -> dict[int, str]:
        pair_ids = list({trade.trading_pair_id for trade in trades})
        pairs = await self.trading_pair_repository.list_by_ids(pair_ids)
        return {pair.id: pair.symbol for pair in pairs}

    @staticmethod
    def _csv_from_rows(rows: list[dict]) -> str:
        if not rows:
            return ""
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ExportService._serialize_value(value) for key, value in row.items()})
        return buffer.getvalue()

    @staticmethod
    def _serialize_value(value):
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _slugify(value: str) -> str:
        return (
            value.lower()
            .replace("/", "_")
            .replace(":", "_")
            .replace(" ", "_")
        )
