from sqlalchemy import Select, desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candle import Candle


class CandleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_many(self, rows: list[dict]) -> int:
        if not rows:
            return 0

        statement = insert(Candle).values(rows)
        statement = statement.on_conflict_do_update(
            constraint="uq_candles_pair_timeframe_open_time",
            set_={
                "close_time": statement.excluded.close_time,
                "open_price": statement.excluded.open_price,
                "high_price": statement.excluded.high_price,
                "low_price": statement.excluded.low_price,
                "close_price": statement.excluded.close_price,
                "volume": statement.excluded.volume,
            },
        )
        result = await self.session.execute(statement)
        return result.rowcount or 0

    async def list_recent(
        self,
        trading_pair_id: int,
        timeframe: str,
        limit: int,
    ) -> list[Candle]:
        query: Select[tuple[Candle]] = (
            select(Candle)
            .where(
                Candle.trading_pair_id == trading_pair_id,
                Candle.timeframe == timeframe,
            )
            .order_by(desc(Candle.open_time))
            .limit(limit)
        )
        result = await self.session.execute(query)
        candles = list(result.scalars().all())
        candles.reverse()
        return candles

    async def list_for_indicator_window(
        self,
        trading_pair_id: int,
        timeframe: str,
        limit: int,
    ) -> list[Candle]:
        return await self.list_recent(
            trading_pair_id=trading_pair_id,
            timeframe=timeframe,
            limit=limit,
        )

    async def list_history(
        self,
        trading_pair_id: int,
        timeframe: str,
        limit: int,
    ) -> list[Candle]:
        query: Select[tuple[Candle]] = (
            select(Candle)
            .where(
                Candle.trading_pair_id == trading_pair_id,
                Candle.timeframe == timeframe,
            )
            .order_by(Candle.open_time.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
