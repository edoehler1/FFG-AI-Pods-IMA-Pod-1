from datetime import datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.contact import Contact
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.models.outreach_action import OutreachAction
from app.services.signal_router import route_signal_to_pwc_people


def _recency_factor(published_at: datetime | None, now: datetime) -> float:
    if not published_at:
        return 0.3
    age_days = (now - published_at).total_seconds() / 86400
    if age_days <= 1:
        return 1.0
    if age_days <= 3:
        return 0.85
    if age_days <= 7:
        return 0.7
    if age_days <= 14:
        return 0.5
    return 0.3


def _relationship_factor(routed: dict, manual_contacts: list) -> float:
    if routed.get("has_grp"):
        return 1.0
    if routed.get("has_account_team"):
        return 0.8
    if routed.get("ranked_contacts"):
        pwc_contacts = [c for c in routed["ranked_contacts"] if c.get("source") == "people_connector"]
        if pwc_contacts:
            return 0.6
    if manual_contacts:
        best = max((c.relationship_strength or 0) for c in manual_contacts)
        return min(best / 5.0, 1.0) if best else 0.3
    return 0.3


def rank_outreach(
    db: Session,
    days: int = 14,
    limit: int = 20,
    include_statuses: list[str] | None = None,
) -> list[dict]:
    if include_statuses is None:
        include_statuses = ["pending"]

    cutoff = datetime.utcnow() - timedelta(days=days)
    now = datetime.utcnow()

    matches = (
        db.query(SignalCompanyMatch, Signal, Company)
        .join(Signal, SignalCompanyMatch.signal_id == Signal.id)
        .join(Company, SignalCompanyMatch.company_id == Company.id)
        .filter(SignalCompanyMatch.created_at >= cutoff)
        .filter(SignalCompanyMatch.match_score.isnot(None))
        .order_by(desc(SignalCompanyMatch.match_score))
        .limit(200)
        .all()
    )

    match_ids = [m.id for m, _, _ in matches]
    actions_by_match = {}
    if match_ids:
        actions = db.query(OutreachAction).filter(OutreachAction.signal_company_match_id.in_(match_ids)).all()
        actions_by_match = {a.signal_company_match_id: a for a in actions}

    company_ids = list({c.id for _, _, c in matches})
    contacts_by_company: dict[str, list] = {}
    if company_ids:
        contacts = db.query(Contact).filter(Contact.company_id.in_(company_ids)).all()
        for c in contacts:
            contacts_by_company.setdefault(c.company_id, []).append(c)

    results: list[dict] = []

    for match, signal, company in matches:
        existing_action = actions_by_match.get(match.id)

        status = existing_action.status if existing_action else "pending"
        action_id = existing_action.id if existing_action else None

        if status not in include_statuses:
            continue

        routed = route_signal_to_pwc_people(db, match, company)
        co_contacts = contacts_by_company.get(company.id, [])

        match_score = match.match_score or 0
        recency = _recency_factor(signal.published_at, now)
        relationship = _relationship_factor(routed, co_contacts)

        composite = match_score * 0.5 + recency * 0.3 + relationship * 0.2

        pipeline_boost = 0.1 if routed.get("has_active_pipeline") else 0.0
        composite = min(composite + pipeline_boost, 1.0)

        urgency = "high" if composite >= 0.6 else "medium" if composite >= 0.35 else "low"

        suggested_contact = None
        if routed.get("ranked_contacts"):
            top = routed["ranked_contacts"][0]
            suggested_contact = {
                "name": top["name"],
                "role": top.get("role"),
                "office": top.get("office"),
                "source": top.get("source", "unknown"),
            }

        results.append({
            "outreach_id": action_id,
            "match_id": match.id,
            "status": status,
            "composite_score": round(composite, 3),
            "urgency": urgency,
            "signal_id": signal.id,
            "signal_title": signal.title,
            "signal_source": signal.source_name,
            "signal_published_at": signal.published_at.isoformat() if signal.published_at else None,
            "signal_type": signal.signal_type,
            "signal_url": signal.url,
            "company_id": company.id,
            "company_name": company.name,
            "client_status": company.client_status,
            "industry": company.industry,
            "match_score": match.match_score,
            "match_type": match.match_type,
            "talking_points": match.talking_points,
            "suggested_contact": suggested_contact,
            "has_grp": routed.get("has_grp", False),
            "has_account_team": routed.get("has_account_team", False),
            "has_active_pipeline": routed.get("has_active_pipeline", False),
            "pipeline": routed.get("pipeline"),
        })

    results.sort(key=lambda r: r["composite_score"], reverse=True)
    return results[:limit]
