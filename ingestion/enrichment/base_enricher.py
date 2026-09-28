"""
Base enricher pattern for MCP integrations.

Each enricher subclass defines:
- mcp_source: the MCP source identifier stored in mcp_enrichments
- stale_days: how many days before a result should be refreshed
- build_prompt(entity): generates the natural-language prompt for the MCP
- entity_type: "company" or "industry"

The base class handles staleness checking, database writes, and the
upsert-or-skip logic.
"""

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.mcp_enrichment import MCPEnrichment


class BaseEnricher(ABC):
    mcp_source: str = ""
    entity_type: str = "company"
    stale_days: int = 90

    def should_refresh(self, db: Session, entity_id: str) -> bool:
        existing = (
            db.query(MCPEnrichment)
            .filter(
                MCPEnrichment.entity_type == self.entity_type,
                MCPEnrichment.entity_id == entity_id,
                MCPEnrichment.mcp_source == self.mcp_source,
            )
            .first()
        )
        if not existing:
            return True
        if existing.stale_after and datetime.now(timezone.utc) >= existing.stale_after:
            return True
        return False

    def store_result(
        self,
        db: Session,
        entity_id: str,
        prompt: str,
        markdown: str,
        summary: dict | None = None,
        citations: list | None = None,
    ) -> MCPEnrichment:
        existing = (
            db.query(MCPEnrichment)
            .filter(
                MCPEnrichment.entity_type == self.entity_type,
                MCPEnrichment.entity_id == entity_id,
                MCPEnrichment.mcp_source == self.mcp_source,
            )
            .first()
        )

        now = datetime.now(timezone.utc)
        stale_after = now + timedelta(days=self.stale_days)

        if existing:
            existing.query_prompt = prompt
            existing.response_markdown = markdown
            existing.response_summary = json.dumps(summary) if summary else None
            existing.citations = json.dumps(citations) if citations else None
            existing.fetched_at = now
            existing.stale_after = stale_after
            db.commit()
            db.refresh(existing)
            return existing

        enrichment = MCPEnrichment(
            id=str(uuid.uuid4()),
            entity_type=self.entity_type,
            entity_id=entity_id,
            mcp_source=self.mcp_source,
            query_prompt=prompt,
            response_markdown=markdown,
            response_summary=json.dumps(summary) if summary else None,
            citations=json.dumps(citations) if citations else None,
            fetched_at=now,
            stale_after=stale_after,
        )
        db.add(enrichment)
        db.commit()
        db.refresh(enrichment)
        return enrichment

    @abstractmethod
    def build_prompts(self, entity) -> list[dict]:
        """Return list of {"prompt": str, "label": str} for MCP calls."""
        pass
