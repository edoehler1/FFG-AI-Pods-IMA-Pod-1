import datetime as dt

from pydantic import BaseModel


class EngagementCreate(BaseModel):
    date: dt.date | None = None
    capabilities_pitched: str | None = None
    project_type: str | None = None
    outcome: str | None = None
    team: str | None = None
    notes: str | None = None


class EngagementOut(BaseModel):
    id: str
    company_id: str
    date: dt.date | None = None
    capabilities_pitched: str | None = None
    project_type: str | None = None
    outcome: str | None = None
    team: str | None = None
    notes: str | None = None
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class EngagementListResponse(BaseModel):
    engagements: list[EngagementOut]
    total: int
