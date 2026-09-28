"""
Relationship service — assembles PwC engagement history + manual contacts
for a company into a unified relationship view.

Reads cached People Connector enrichment data (from people_engagements enricher)
and combines it with manually-entered contacts and engagements.
Returns structured data grouped by service line when available.
"""

import json

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.mcp_enrichment import MCPEnrichment
from app.services.enrichment_reader import get_enrichment_text

STRATEGY_KEYWORDS = ["strategy", "consulting solutions", "enterprise cost", "value realization",
                     "operations strategy", "manufacturing strategy", "transformation"]
STRATEGY_SERVICE_LINES = ["strategy", "consulting"]


def _is_strategy_engagement(eng: dict) -> bool:
    name = (eng.get("name") or "").lower()
    service_line = (eng.get("service_line") or "").lower()
    for kw in STRATEGY_KEYWORDS:
        if kw in name or kw in service_line:
            return True
    for sl in STRATEGY_SERVICE_LINES:
        if sl in service_line:
            return True
    return False


def _sort_engagements(engs: list[dict]) -> list[dict]:
    return sorted(engs, key=lambda e: e.get("start_date") or "9999", reverse=True)


def _group_engagements(engagements: list[dict]) -> dict:
    strategy = []
    other_groups: dict[str, list[dict]] = {}

    for eng in engagements:
        if _is_strategy_engagement(eng):
            strategy.append(eng)
        else:
            label = eng.get("service_line") or "Other Advisory"
            other_groups.setdefault(label, []).append(eng)

    return {
        "strategy": _sort_engagements(strategy),
        "other": [
            {"service_line": label, "engagements": _sort_engagements(engs)}
            for label, engs in sorted(other_groups.items())
        ],
    }


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

    structured = None
    if enrichment_record and enrichment_record.response_summary:
        try:
            structured = json.loads(enrichment_record.response_summary)
        except (json.JSONDecodeError, TypeError):
            pass

    grouped_engagements = None
    if structured and structured.get("engagements"):
        grouped_engagements = _group_engagements(structured["engagements"])

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
        "pwc_structured": structured,
        "pwc_grouped_engagements": grouped_engagements,
        "manual_contacts": contacts,
        "manual_engagements": engagements,
        "has_pwc_data": people_eng is not None,
    }


def build_relationship_refresh_prompts(company: Company) -> list[dict]:
    return [
        {
            "mcp_tool": "engagement_client_finder",
            "label": f"PwC advisory engagement history for {company.name}",
            "prompt": (
                f"Who at PwC has worked with {company.name} on advisory engagements? "
                f"Include the GRP and account team. Filter to Advisory LoS only — "
                f"exclude Assurance, Tax, and audit. Show engagement names, dates, "
                f"staff with roles and offices. Use group_by='engagement', los='Advisory'."
            ),
        },
    ]
