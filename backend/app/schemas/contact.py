import datetime as dt

from pydantic import BaseModel


class ContactCreate(BaseModel):
    name: str
    title: str | None = None
    email: str | None = None
    relationship_strength: int | None = None
    last_interaction_date: dt.date | None = None
    notes: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    title: str | None = None
    email: str | None = None
    relationship_strength: int | None = None
    last_interaction_date: dt.date | None = None
    notes: str | None = None


class ContactOut(BaseModel):
    id: str
    company_id: str
    name: str
    title: str | None = None
    email: str | None = None
    relationship_strength: int | None = None
    last_interaction_date: dt.date | None = None
    notes: str | None = None
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class ContactListResponse(BaseModel):
    contacts: list[ContactOut]
    total: int
