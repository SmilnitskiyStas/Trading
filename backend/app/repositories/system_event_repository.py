from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_event import SystemEvent


class SystemEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, event: SystemEvent) -> SystemEvent:
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_recent(self, limit: int = 100, event_type: str | None = None) -> list[SystemEvent]:
        query: Select[tuple[SystemEvent]] = select(SystemEvent)
        if event_type:
            query = query.where(SystemEvent.event_type == event_type)
        query = query.order_by(desc(SystemEvent.created_at)).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
