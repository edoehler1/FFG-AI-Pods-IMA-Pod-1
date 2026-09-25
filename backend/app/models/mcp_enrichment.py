import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MCPEnrichment(Base):
    __tablename__ = "mcp_enrichments"
    __table_args__ = (
        Index("ix_mcp_enrichments_entity_source", "entity_type", "entity_id", "mcp_source"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    mcp_source: Mapped[str] = mapped_column(String(50), nullable=False)
    query_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    response_summary: Mapped[str | None] = mapped_column(Text)
    citations: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    stale_after: Mapped[datetime | None] = mapped_column(DateTime)
