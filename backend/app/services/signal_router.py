"""
Signal router — Stage 5 of the matching pipeline.

Given a signal-company match, looks up the company's PwC engagement history
and returns a ranked list of who at PwC should act on this signal.

Priority order: GRP > account team > recent engagement staff > manual contacts.
"""

import json
import re

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.signal_company import SignalCompanyMatch
from app.services.enrichment_reader import get_enrichment_text


def route_signal_to_pwc_people(
    db: Session,
    match: SignalCompanyMatch,
    company: Company,
) -> dict:
    people_eng = get_enrichment_text(
        db, "company", company.id, "people_engagements", max_age_days=30
    )

    manual_contacts = [
        {
            "name": c.name,
            "title": c.title,
            "source": "manual",
            "priority": _contact_priority(c.relationship_strength),
        }
        for c in company.contacts
    ]

    pwc_summary = None
    if people_eng:
        pwc_summary = people_eng[:500]

    salesforce = get_enrichment_text(
        db, "company", company.id, "salesforce", max_age_days=14
    )

    return {
        "signal_id": match.signal_id,
        "company_id": match.company_id,
        "company_name": company.name,
        "match_score": match.match_score,
        "pwc_engagement_summary": pwc_summary,
        "manual_contacts": manual_contacts,
        "has_active_pipeline": salesforce is not None,
        "pipeline_summary": salesforce[:200] if salesforce else None,
    }


def route_all_matches(
    db: Session,
    matches: list[SignalCompanyMatch],
    companies_by_id: dict[str, Company],
) -> list[dict]:
    results = []
    for match in matches:
        company = companies_by_id.get(match.company_id)
        if not company:
            continue
        routed = route_signal_to_pwc_people(db, match, company)
        results.append(routed)

    results.sort(key=lambda r: (r["match_score"] or 0), reverse=True)
    return results


def _contact_priority(strength: int | None) -> int:
    if not strength:
        return 5
    return 6 - strength
