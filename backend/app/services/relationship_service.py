"""
Relationship service — assembles PwC engagement history + manual contacts
for a company into a unified relationship view.

Reads cached People Connector enrichment data (from people_engagements enricher)
and combines it with manually-entered contacts and engagements.
"""

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.mcp_enrichment import MCPEnrichment
from app.services.enrichment_reader import get_enrichment_text


def get_relationship_summary(db: Session, company: Company) -> dict:
    people_eng = get_enrichment_text(
        db, "company", company.id, "people_engagements", max_age_days=30
    )

    enrichment_record = (
        db.query(MCPEnrichment)
        .filter(
            MCPEnrichment.entity_type == "company",
            MCPEnrichment.entity_id == company.id,
            MCPEnrichment.mcp_source == "people_engagements",
        )
        .first()
    )

    contacts = [
        {
            "name": c.name,
            "title": c.title,
            "email": c.email,
            "relationship_strength": c.relationship_strength,
            "last_interaction_date": c.last_interaction_date,
            "notes": c.notes,
        }
        for c in company.contacts
    ]

    engagements = [
        {
            "date": e.date,
            "project_type": e.project_type,
            "capabilities_pitched": e.capabilities_pitched,
            "outcome": e.outcome,
            "team": e.team,
            "notes": e.notes,
        }
        for e in company.engagements
    ]

    return {
        "company_id": company.id,
        "company_name": company.name,
        "pwc_engagement_history": people_eng,
        "pwc_engagement_fetched_at": (
            enrichment_record.fetched_at.isoformat() if enrichment_record else None
        ),
        "manual_contacts": contacts,
        "manual_engagements": engagements,
        "has_pwc_data": people_eng is not None,
    }


def build_relationship_refresh_prompts(company: Company) -> list[dict]:
    """Return MCP prompts a Claude Code session can execute to refresh relationship data."""
    return [
        {
            "mcp_tool": "engagement_client_finder",
            "label": f"PwC engagement history for {company.name}",
            "prompt": (
                f"Who at PwC has worked with {company.name}? "
                f"Include the Global Relationship Partner (GRP), account team members, "
                f"people who have billed time to engagements for this company, "
                f"and any recent engagement history. "
                f"For key people, include their office location and seniority level."
            ),
        },
        {
            "mcp_tool": "find_people",
            "label": f"PwC people with {company.name} experience",
            "prompt": (
                f"Find PwC people who have worked with {company.name} "
                f"or have experience in the {company.industry or 'EFS'} sector. "
                f"Include their seniority, office location, and relevant skills."
            ),
        },
    ]
