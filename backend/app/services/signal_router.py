"""
Signal router — Stage 5 of the matching pipeline.

Given a signal-company match, looks up the company's PwC engagement history
and Salesforce pipeline, and returns a ranked list of who should act.

Priority order: GRP (1) > account team (2) > engagement staff (3) > manual contacts (4-5).
"""

import json

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.signal_company import SignalCompanyMatch
from app.services.enrichment_reader import get_enrichment


def route_signal_to_pwc_people(
    db: Session,
    match: SignalCompanyMatch,
    company: Company,
) -> dict:
    ranked_contacts = []

    people_data = _get_structured_people(db, company.id)
    if people_data:
        if people_data.get("grp"):
            grp = people_data["grp"]
            ranked_contacts.append({
                "name": grp["name"],
                "role": "GRP",
                "office": grp.get("office"),
                "source": "people_connector",
                "priority": 1,
            })
        for person in people_data.get("account_team", []):
            ranked_contacts.append({
                "name": person["name"],
                "role": person.get("role", "Account Team"),
                "office": person.get("office"),
                "source": "people_connector",
                "priority": 2,
            })
        for person in people_data.get("engagement_staff", []):
            ranked_contacts.append({
                "name": person["name"],
                "role": person.get("role", "Engagement Staff"),
                "office": person.get("office"),
                "source": "people_connector",
                "priority": 3,
            })

    for contact in sorted(company.contacts, key=lambda c: c.relationship_strength or 0, reverse=True):
        ranked_contacts.append({
            "name": contact.name,
            "role": contact.title,
            "office": None,
            "source": "manual",
            "priority": _contact_priority(contact.relationship_strength),
        })

    pipeline = _get_structured_pipeline(db, company.id)

    return {
        "signal_id": match.signal_id,
        "company_id": match.company_id,
        "company_name": company.name,
        "match_score": match.match_score,
        "ranked_contacts": ranked_contacts,
        "has_grp": people_data.get("has_grp", False) if people_data else False,
        "has_account_team": people_data.get("has_account_team", False) if people_data else False,
        "has_active_pipeline": pipeline is not None,
        "pipeline": pipeline,
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


def _get_structured_people(db: Session, company_id: str) -> dict | None:
    enrichment = get_enrichment(db, "company", company_id, "people_engagements")
    if not enrichment or not enrichment.response_summary:
        return None
    try:
        return json.loads(enrichment.response_summary)
    except (json.JSONDecodeError, TypeError):
        return None


def _get_structured_pipeline(db: Session, company_id: str) -> dict | None:
    enrichment = get_enrichment(db, "company", company_id, "salesforce")
    if not enrichment or not enrichment.response_summary:
        return None
    try:
        data = json.loads(enrichment.response_summary)
    except (json.JSONDecodeError, TypeError):
        return None

    if not data.get("opportunities"):
        return None

    nearest_close = None
    for opp in data["opportunities"]:
        if opp.get("close_date"):
            nearest_close = opp["close_date"]
            break

    top_opp = data["opportunities"][0] if data["opportunities"] else None

    return {
        "total_value": data.get("total_pipeline_value"),
        "opportunity_count": data.get("opportunity_count", 0),
        "nearest_close": nearest_close,
        "top_opportunity": top_opp,
    }


def _contact_priority(strength: int | None) -> int:
    if not strength:
        return 5
    return 6 - strength
