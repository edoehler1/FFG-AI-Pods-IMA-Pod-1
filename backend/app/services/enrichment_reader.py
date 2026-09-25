"""
Reads MCP enrichment data from the database for use in LLM prompts.

Each function returns a formatted string ready to inject into a prompt section,
or None if no enrichment data exists for the given entity.
"""

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.mcp_enrichment import MCPEnrichment

INDUSTRY_SLUG_MAP = {
    "aerospace": "aerospace_defense",
    "a&d": "aerospace_defense",
    "defense": "aerospace_defense",
    "auto": "automotive",
}


def _normalize_industry(raw: str | None) -> str | None:
    if not raw:
        return None
    return INDUSTRY_SLUG_MAP.get(raw.lower(), raw)


def get_enrichment(
    db: Session,
    entity_type: str,
    entity_id: str,
    mcp_source: str,
) -> MCPEnrichment | None:
    return (
        db.query(MCPEnrichment)
        .filter(
            MCPEnrichment.entity_type == entity_type,
            MCPEnrichment.entity_id == entity_id,
            MCPEnrichment.mcp_source == mcp_source,
        )
        .order_by(desc(MCPEnrichment.fetched_at))
        .first()
    )


def get_all_enrichments_for_entity(
    db: Session,
    entity_type: str,
    entity_id: str,
) -> list[MCPEnrichment]:
    return (
        db.query(MCPEnrichment)
        .filter(
            MCPEnrichment.entity_type == entity_type,
            MCPEnrichment.entity_id == entity_id,
        )
        .order_by(desc(MCPEnrichment.fetched_at))
        .all()
    )


def get_enrichment_text(
    db: Session,
    entity_type: str,
    entity_id: str,
    mcp_source: str,
    max_age_days: int | None = None,
) -> str | None:
    enrichment = get_enrichment(db, entity_type, entity_id, mcp_source)
    if not enrichment:
        return None
    if max_age_days and enrichment.fetched_at:
        age = (datetime.utcnow() - enrichment.fetched_at).days
        if age > max_age_days:
            return None
    return enrichment.response_markdown


def build_enrichment_context(db: Session, company_id: str, company_industry: str | None = None) -> str:
    """Assembles all available MCP enrichment data for a company into prompt-ready sections."""
    sections = []

    capiq = get_enrichment_text(db, "company", company_id, "capiq", max_age_days=90)
    if capiq:
        sections.append(f"## Capital IQ Financial Intelligence\n{capiq}")

    sec_risk = get_enrichment_text(db, "company", company_id, "sec_mcp_risk", max_age_days=90)
    if sec_risk:
        sections.append(f"## SEC Filing Analysis — Risk Factors\n{sec_risk}")

    sec_mda = get_enrichment_text(db, "company", company_id, "sec_mcp_mda", max_age_days=90)
    if sec_mda:
        sections.append(f"## SEC Filing Analysis — MD&A\n{sec_mda}")

    earnings = get_enrichment_text(db, "company", company_id, "earnings", max_age_days=90)
    if earnings:
        sections.append(f"## Latest Earnings Call Highlights\n{earnings}")

    factiva = get_enrichment_text(db, "company", company_id, "factiva", max_age_days=7)
    if factiva:
        sections.append(f"## Licensed Press Coverage (Factiva)\n{factiva}")

    boardex = get_enrichment_text(db, "company", company_id, "boardex", max_age_days=30)
    if boardex:
        sections.append(f"## Executive & Board Intelligence (BoardEx)\n{boardex}")

    emis = get_enrichment_text(db, "company", company_id, "emis", max_age_days=90)
    if emis:
        sections.append(f"## Ownership & Corporate Structure (EMIS)\n{emis}")

    web = get_enrichment_text(db, "company", company_id, "web", max_age_days=30)
    if web:
        sections.append(f"## Open Web Intelligence\n{web}")

    industry = _normalize_industry(company_industry)
    if industry:
        ibis = get_enrichment_text(db, "industry", industry, "ibis", max_age_days=30)
        if ibis:
            sections.append(f"## Industry Landscape (IBISWorld)\n{ibis}")

        connected = get_enrichment_text(db, "industry", industry, "connectedsource", max_age_days=30)
        if connected:
            sections.append(f"## PwC Industry Insights\n{connected}")

        vim = get_enrichment_text(db, "industry", industry, "vim", max_age_days=90)
        if vim:
            sections.append(f"## Value Shifts (PwC VIM)\n{vim}")

        ceo = get_enrichment_text(db, "industry", industry, "ceo_survey", max_age_days=180)
        if ceo:
            sections.append(f"## CEO Survey Insights\n{ceo}")

    return "\n\n".join(sections) if sections else ""
