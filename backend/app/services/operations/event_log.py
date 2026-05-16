from app.core.logging import get_logger
from app.models.system_event import SystemEvent
from app.repositories.system_event_repository import SystemEventRepository


class EventLogService:
    def __init__(self, event_repository: SystemEventRepository):
        self.event_repository = event_repository
        self.logger = get_logger("app.operations.events")

    async def record(
        self,
        event_type: str,
        level: str,
        message: str,
        payload: dict | None = None,
        account_id: int | None = None,
        paper_trade_id: int | None = None,
    ) -> SystemEvent:
        getattr(self.logger, level.lower(), self.logger.info)(message)
        event = SystemEvent(
            account_id=account_id,
            paper_trade_id=paper_trade_id,
            event_type=event_type,
            level=level.upper(),
            message=message,
            payload=payload,
        )
        return await self.event_repository.create(event)
