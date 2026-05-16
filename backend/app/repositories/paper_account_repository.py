from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper_account import PaperAccount


class PaperAccountRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_name(self, name: str) -> PaperAccount | None:
        result = await self.session.execute(select(PaperAccount).where(PaperAccount.name == name))
        return result.scalar_one_or_none()

    async def get_or_create(self, name: str, initial_balance: Decimal) -> PaperAccount:
        account = await self.get_by_name(name)
        if account is not None:
            return account

        account = PaperAccount(
            name=name,
            initial_balance=initial_balance,
            current_balance=initial_balance,
            is_active=True,
        )
        self.session.add(account)
        await self.session.flush()
        return account

