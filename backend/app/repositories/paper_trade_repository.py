from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper_trade import PaperTrade


class PaperTradeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_recent(self, account_id: int, limit: int = 100) -> list[PaperTrade]:
        query: Select[tuple[PaperTrade]] = (
            select(PaperTrade)
            .where(PaperTrade.account_id == account_id)
            .order_by(PaperTrade.opened_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_all_for_account(self, account_id: int) -> list[PaperTrade]:
        query: Select[tuple[PaperTrade]] = (
            select(PaperTrade)
            .where(PaperTrade.account_id == account_id)
            .order_by(PaperTrade.opened_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_open_positions(self, account_id: int) -> int:
        result = await self.session.execute(
            select(PaperTrade).where(
                PaperTrade.account_id == account_id,
                PaperTrade.status == "OPEN",
            )
        )
        return len(list(result.scalars().all()))

    async def get_open_trade_for_symbol(
        self,
        account_id: int,
        trading_pair_id: int,
        timeframe: str,
    ) -> PaperTrade | None:
        result = await self.session.execute(
            select(PaperTrade).where(
                PaperTrade.account_id == account_id,
                PaperTrade.trading_pair_id == trading_pair_id,
                PaperTrade.timeframe == timeframe,
                PaperTrade.status == "OPEN",
            )
        )
        return result.scalar_one_or_none()

    async def create(self, trade: PaperTrade) -> PaperTrade:
        self.session.add(trade)
        await self.session.flush()
        return trade
