from datetime import datetime

from pydantic import BaseModel


class CompanyCreate(BaseModel):
    name: str
    industry: str | None = None
    sub_sector: str | None = None
    size: str | None = None
    geography: str | None = None
    client_status: str = "target"
    website: str | None = None
    notes: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    sub_sector: str | None = None
    size: str | None = None
    geography: str | None = None
    client_status: str | None = None
    website: str | None = None
    notes: str | None = None


class CompanyOut(BaseModel):
    id: str
    name: str
    industry: str | None = None
    sub_sector: str | None = None
    size: str | None = None
    geography: str | None = None
    client_status: str
    website: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CompanyListResponse(BaseModel):
    companies: list[CompanyOut]
    total: int
    page: int
    page_size: int
