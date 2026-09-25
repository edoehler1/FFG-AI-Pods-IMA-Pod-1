from datetime import datetime

from pydantic import BaseModel


class EnrichmentCreate(BaseModel):
    entity_type: str
    entity_id: str
    mcp_source: str
    query_prompt: str
    response_markdown: str
    response_summary: str | None = None
    citations: str | None = None
    stale_after: datetime | None = None


class EnrichmentOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    mcp_source: str
    query_prompt: str
    response_markdown: str
    response_summary: str | None = None
    citations: str | None = None
    fetched_at: datetime
    stale_after: datetime | None = None

    model_config = {"from_attributes": True}


class EnrichmentListResponse(BaseModel):
    enrichments: list[EnrichmentOut]
    total: int
