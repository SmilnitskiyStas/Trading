from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SystemEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int | None
    paper_trade_id: int | None
    event_type: str
    level: str
    message: str
    payload: dict | None
    created_at: datetime
