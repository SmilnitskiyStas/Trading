from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange import Exchange


class ExchangeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_slug(self, slug: str) -> Exchange | None:
        result = await self.session.execute(select(Exchange).where(Exchange.slug == slug))
        return result.scalar_one_or_none()

    async def get_or_create(self, slug: str, name: str | None = None) -> Exchange:
        exchange = await self.get_by_slug(slug)
        if exchange is not None:
            return exchange

        exchange = Exchange(
            slug=slug,
            name=name or slug.upper(),
            is_active=True,
        )
        self.session.add(exchange)
        await self.session.flush()
        return exchange

