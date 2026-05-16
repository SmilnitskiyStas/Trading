from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_report_history import DailyReportHistory


class DailyReportHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, report: DailyReportHistory) -> DailyReportHistory:
        self.session.add(report)
        await self.session.flush()
        return report

    async def list_recent(self, limit: int = 30, account_name: str | None = None) -> list[DailyReportHistory]:
        query: Select[tuple[DailyReportHistory]] = select(DailyReportHistory)
        if account_name:
            query = query.where(DailyReportHistory.account_name == account_name)
        query = query.order_by(desc(DailyReportHistory.created_at)).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
