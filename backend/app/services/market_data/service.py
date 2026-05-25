from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.candle import Candle
from app.repositories.candle_repository import CandleRepository
from app.repositories.exchange_repository import ExchangeRepository
from app.repositories.trading_pair_repository import TradingPairRepository
from app.schemas.market_data import MarketDataSyncRequest, MarketDataSyncResponse
from app.services.market_data.ccxt_client import CcxtMarketDataClient


class MarketDataService:
    MAX_FETCH_BATCH_SIZE = 1000

    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.exchange_repository = ExchangeRepository(session)
        self.trading_pair_repository = TradingPairRepository(session)
        self.candle_repository = CandleRepository(session)

    async def list_candles(
        self,
        exchange_slug: str,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[Candle]:
        exchange = await self.exchange_repository.get_by_slug(exchange_slug)
        if exchange is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exchange '{exchange_slug}' is not configured.",
            )

        trading_pair = await self.trading_pair_repository.get_by_exchange_and_symbol(exchange.id, symbol)
        if trading_pair is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trading pair '{symbol}' is not configured for exchange '{exchange_slug}'.",
            )

        return await self.candle_repository.list_recent(
            trading_pair_id=trading_pair.id,
            timeframe=timeframe,
            limit=limit,
        )

    async def sync_ohlcv(self, payload: MarketDataSyncRequest) -> MarketDataSyncResponse:
        self._validate_request(payload)

        exchange = await self.exchange_repository.get_or_create(
            slug=payload.exchange,
            name=payload.exchange.upper(),
        )
        base_asset, quote_asset = self._split_symbol(payload.symbol)
        trading_pair = await self.trading_pair_repository.get_or_create(
            exchange_id=exchange.id,
            symbol=payload.symbol,
            base_asset=base_asset,
            quote_asset=quote_asset,
        )

        client = CcxtMarketDataClient(payload.exchange)
        try:
            raw_ohlcv = await self._fetch_ohlcv_window(
                client=client,
                symbol=payload.symbol,
                timeframe=payload.timeframe,
                total_limit=payload.limit,
            )
        except AttributeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exchange client '{payload.exchange}' is not available.",
            ) from exc
        except Exception as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to fetch OHLCV from '{payload.exchange}': {exc}",
            ) from exc

        rows = [
            self._normalize_candle_row(
                trading_pair_id=trading_pair.id,
                timeframe=payload.timeframe,
                item=item,
            )
            for item in raw_ohlcv
        ]

        stored_count = await self.candle_repository.upsert_many(rows)
        await self.session.commit()

        return MarketDataSyncResponse(
            exchange=payload.exchange,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            fetched_count=len(raw_ohlcv),
            stored_count=stored_count,
            status="ok",
        )

    def _validate_request(self, payload: MarketDataSyncRequest) -> None:
        if payload.exchange != self.settings.market_data_exchange:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exchange '{payload.exchange}' is not enabled for MVP.",
            )

        if payload.symbol not in self.settings.market_data_symbol_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Symbol '{payload.symbol}' is not enabled for MVP.",
            )

        if payload.timeframe not in self.settings.market_data_timeframe_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Timeframe '{payload.timeframe}' is not enabled for MVP.",
            )

    @staticmethod
    def _split_symbol(symbol: str) -> tuple[str, str]:
        parts = symbol.split("/")
        if len(parts) != 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported symbol format '{symbol}'. Expected BASE/QUOTE.",
            )
        return parts[0], parts[1]

    @staticmethod
    def _normalize_candle_row(
        trading_pair_id: int,
        timeframe: str,
        item: list[float] | tuple[float, ...],
    ) -> dict:
        open_timestamp, open_price, high_price, low_price, close_price, volume = item[:6]
        open_time = datetime.fromtimestamp(open_timestamp / 1000, tz=UTC)
        close_time = open_time + MarketDataService._timeframe_delta(timeframe)

        return {
            "trading_pair_id": trading_pair_id,
            "timeframe": timeframe,
            "open_time": open_time,
            "close_time": close_time,
            "open_price": Decimal(str(open_price)),
            "high_price": Decimal(str(high_price)),
            "low_price": Decimal(str(low_price)),
            "close_price": Decimal(str(close_price)),
            "volume": Decimal(str(volume)),
        }

    @staticmethod
    def _timeframe_delta(timeframe: str) -> timedelta:
        if len(timeframe) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported timeframe '{timeframe}' for MVP.",
            )

        amount_raw = timeframe[:-1]
        unit = timeframe[-1]
        if not amount_raw.isdigit():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported timeframe '{timeframe}' for MVP.",
            )

        amount = int(amount_raw)
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported timeframe '{timeframe}' for MVP.",
            )

        unit_mapping = {
            "m": timedelta(minutes=amount),
            "h": timedelta(hours=amount),
            "d": timedelta(days=amount),
        }
        if unit not in unit_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported timeframe '{timeframe}' for MVP.",
            )

        return unit_mapping[unit]

    async def _fetch_ohlcv_window(
        self,
        client: CcxtMarketDataClient,
        symbol: str,
        timeframe: str,
        total_limit: int,
    ) -> list[list[float] | tuple[float, ...]]:
        if total_limit <= self.MAX_FETCH_BATCH_SIZE:
            return list(
                await client.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=total_limit,
                )
            )

        timeframe_delta = self._timeframe_delta(timeframe)
        timeframe_ms = int(timeframe_delta.total_seconds() * 1000)
        now_ms = int(datetime.now(tz=UTC).timestamp() * 1000)
        cursor_since = now_ms - (total_limit * timeframe_ms)
        remaining = total_limit
        all_rows: list[list[float] | tuple[float, ...]] = []
        last_open_timestamp: int | None = None

        while remaining > 0:
            batch_limit = min(self.MAX_FETCH_BATCH_SIZE, remaining)
            batch = list(
                await client.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=cursor_since,
                    limit=batch_limit,
                )
            )
            if not batch:
                break

            filtered_batch = [
                item for item in batch
                if last_open_timestamp is None or int(item[0]) > last_open_timestamp
            ]
            if not filtered_batch:
                break

            all_rows.extend(filtered_batch)
            last_open_timestamp = int(filtered_batch[-1][0])
            remaining = total_limit - len(all_rows)
            cursor_since = last_open_timestamp + timeframe_ms

            if len(filtered_batch) < batch_limit:
                break

        return all_rows[-total_limit:]
