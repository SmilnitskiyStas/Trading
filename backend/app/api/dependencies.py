from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.market_data.service import MarketDataService


async def get_market_data_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[MarketDataService]:
    yield MarketDataService(session=session)
