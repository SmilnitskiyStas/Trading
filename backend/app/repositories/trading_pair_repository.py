from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trading_pair import TradingPair


class TradingPairRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_exchange_and_symbol(self, exchange_id: int, symbol: str) -> TradingPair | None:
        result = await self.session.execute(
            select(TradingPair).where(
                TradingPair.exchange_id == exchange_id,
                TradingPair.symbol == symbol,
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        exchange_id: int,
        symbol: str,
        base_asset: str,
        quote_asset: str,
    ) -> TradingPair:
        trading_pair = await self.get_by_exchange_and_symbol(exchange_id, symbol)
        if trading_pair is not None:
            return trading_pair

        trading_pair = TradingPair(
            exchange_id=exchange_id,
            symbol=symbol,
            base_asset=base_asset,
            quote_asset=quote_asset,
            is_active=True,
        )
        self.session.add(trading_pair)
        await self.session.flush()
        return trading_pair

    async def list_by_ids(self, ids: list[int]) -> list[TradingPair]:
        if not ids:
            return []
        result = await self.session.execute(
            select(TradingPair).where(TradingPair.id.in_(ids))
        )
        return list(result.scalars().all())
