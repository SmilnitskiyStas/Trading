from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.paper_trading import get_paper_trading_service
from app.db.session import get_db_session
from app.repositories.daily_report_history_repository import DailyReportHistoryRepository
from app.schemas.reports import DailyReportHistoryRead
from app.services.execution.paper_trading import PaperTradingService
from app.services.automation.runner import automation_runner
from app.services.reports.daily_report import DailyReportService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def get_daily_report_service(
    session: AsyncSession = Depends(get_db_session),
    paper_trading_service: PaperTradingService = Depends(get_paper_trading_service),
) -> DailyReportService:
    return DailyReportService(session=session, paper_trading_service=paper_trading_service)


@router.get("/daily/preview")
async def preview_daily_report(
    account_name: str = Query(default="paper-main"),
    report_service: DailyReportService = Depends(get_daily_report_service),
) -> dict:
    return await report_service.build_preview(
        account_name=account_name,
        automation_status=automation_runner.get_status(),
    )


@router.post("/daily/send")
async def send_daily_report(
    account_name: str = Query(default="paper-main"),
    force: bool = Query(default=True),
    report_service: DailyReportService = Depends(get_daily_report_service),
) -> dict:
    return await report_service.send_report(
        account_name=account_name,
        automation_status=automation_runner.get_status(),
        force=force,
    )


@router.get("/daily/history", response_model=list[DailyReportHistoryRead])
async def list_daily_report_history(
    account_name: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[DailyReportHistoryRead]:
    repository = DailyReportHistoryRepository(session)
    rows = await repository.list_recent(limit=limit, account_name=account_name)
    return [DailyReportHistoryRead.model_validate(row) for row in rows]
