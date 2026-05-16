from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class DailyReportHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int | None
    account_name: str
    report_date: date
    timezone: str
    trigger_type: str
    status: str
    message: str
    detail: str | None
    created_at: datetime
