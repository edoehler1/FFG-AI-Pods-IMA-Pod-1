from datetime import datetime

from pydantic import BaseModel


class SignalOut(BaseModel):
    id: str
    title: str
    body: str | None = None
    url: str | None = None
    source_name: str
    published_at: datetime | None = None
    industry: str | None = None
    sub_sector: str | None = None
    signal_type: str | None = None
    importance_score: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalListResponse(BaseModel):
    signals: list[SignalOut]
    total: int
    page: int
    page_size: int
