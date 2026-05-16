from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.system_event_repository import SystemEventRepository
from app.schemas.system_event import SystemEventRead
from app.services.notifications.telegram import TelegramNotifier

router = APIRouter(prefix="/api/v1", tags=["system-events"])


@router.get("/events", response_model=list[SystemEventRead])
async def list_system_events(
    limit: int = Query(default=100, ge=1, le=500),
    event_type: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> list[SystemEventRead]:
    repository = SystemEventRepository(session)
    events = await repository.list_recent(limit=limit, event_type=event_type)
    return [SystemEventRead.model_validate(event) for event in events]


@router.post("/notifications/test")
async def send_test_notification() -> dict[str, bool]:
    notifier = TelegramNotifier()
    delivered = await notifier.send_message("Trading bot test notification: Telegram integration is configured.")
    return {"delivered": delivered}
