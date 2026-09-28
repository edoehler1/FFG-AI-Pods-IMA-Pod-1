from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.contact import Contact
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.models.weekly_report import WeeklyReport
from app.models.mcp_enrichment import MCPEnrichment
from app.services.enrichment_reader import get_enrichment_text
from app.services.signal_router import route_signal_to_pwc_people

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(
    days: int = Query(7, ge=1, le=30, description="Lookback window in days"),
    top_n: int = Query(5, ge=1, le=20, description="Number of top actions to return"),
    db: Session = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days)

    top_actions = _build_top_actions(db, cutoff, top_n)
    portfolio_pulse = _build_portfolio_pulse(db, cutoff)
    pipeline_summary = _build_pipeline_summary(db)

    return {
        "top_actions": top_actions,
        "portfolio_pulse": portfolio_pulse,
        "pipeline_summary": pipeline_summary,
        "generated_at": datetime.utcnow().isoformat(),
        "lookback_days": days,
    }


def _build_top_actions(db: Session, cutoff: datetime, top_n: int) -> list[dict]:
    matches = (
        db.query(SignalCompanyMatch, Signal, Company)
        .join(Signal, SignalCompanyMatch.signal_id == Signal.id)
        .join(Company, SignalCompanyMatch.company_id == Company.id)
        .filter(SignalCompanyMatch.created_at >= cutoff)
        .filter(SignalCompanyMatch.match_score.isnot(None))
        .order_by(desc(SignalCompanyMatch.match_score))
        .limit(top_n * 3)
        .all()
    )

    seen_companies: set[str] = set()
    actions: list[dict] = []

    for match, signal, company in matches:
        if len(actions) >= top_n:
            break
        if company.id in seen_companies:
            continue
        seen_companies.add(company.id)

        routed = route_signal_to_pwc_people(db, match, company)

        best_contact = None
        if company.contacts:
            sorted_contacts = sorted(
                company.contacts,
                key=lambda c: c.relationship_strength or 0,
                reverse=True,
            )
            c = sorted_contacts[0]
            best_contact = {
                "name": c.name,
                "title": c.title,
                "relationship_strength": c.relationship_strength,
            }

        urgency = "high" if (match.match_score or 0) >= 0.7 else "medium" if (match.match_score or 0) >= 0.4 else "low"

        actions.append({
            "signal_id": signal.id,
            "signal_title": signal.title,
            "signal_source": signal.source_name,
            "signal_published_at": signal.published_at.isoformat() if signal.published_at else None,
            "signal_type": signal.signal_type,
            "company_id": company.id,
            "company_name": company.name,
            "client_status": company.client_status,
            "industry": company.industry,
            "match_score": match.match_score,
            "match_type": match.match_type,
            "talking_points": match.talking_points,
            "suggested_contact": best_contact,
            "pwc_engagement_summary": routed.get("pwc_engagement_summary"),
            "has_active_pipeline": routed.get("has_active_pipeline", False),
            "urgency": urgency,
        })

    return actions


def _build_portfolio_pulse(db: Session, cutoff: datetime) -> list[dict]:
    companies = (
        db.query(Company)
        .filter(Company.client_status.in_(["active", "target", "past"]))
        .order_by(Company.client_status, Company.name)
        .all()
    )

    pulse: list[dict] = []
    for company in companies:
        signal_count = (
            db.query(func.count(SignalCompanyMatch.id))
            .join(Signal, SignalCompanyMatch.signal_id == Signal.id)
            .filter(SignalCompanyMatch.company_id == company.id)
            .filter(SignalCompanyMatch.created_at >= cutoff)
            .scalar()
        ) or 0

        latest_report = (
            db.query(WeeklyReport)
            .filter(WeeklyReport.company_id == company.id)
            .order_by(desc(WeeklyReport.generated_at))
            .first()
        )

        last_contact = None
        if company.contacts:
            dates = [c.last_interaction_date for c in company.contacts if c.last_interaction_date]
            if dates:
                last_contact = max(dates).isoformat()

        pulse.append({
            "company_id": company.id,
            "company_name": company.name,
            "client_status": company.client_status,
            "industry": company.industry,
            "signal_count": signal_count,
            "has_opportunity": latest_report.has_opportunity if latest_report else False,
            "last_report_date": latest_report.generated_at.isoformat() if latest_report else None,
            "last_interaction_date": last_contact,
        })

    return pulse


def _build_pipeline_summary(db: Session) -> dict:
    from datetime import datetime, timedelta
    import json

    cutoff = datetime.utcnow() - timedelta(days=14)
    salesforce_enrichments = (
        db.query(MCPEnrichment)
        .filter(MCPEnrichment.mcp_source == "salesforce")
        .filter(MCPEnrichment.entity_type == "company")
        .filter(MCPEnrichment.fetched_at >= cutoff)
        .all()
    )

    if not salesforce_enrichments:
        return {"available": False, "companies_with_data": 0}

    company_summaries: list[dict] = []
    for enrichment in salesforce_enrichments:
        company = db.query(Company).filter(Company.id == enrichment.entity_id).first()
        if not company:
            continue

        structured = None
        if enrichment.response_summary:
            try:
                structured = json.loads(enrichment.response_summary)
            except (json.JSONDecodeError, TypeError):
                pass

        if structured and isinstance(structured, dict):
            summary_text = structured.get("summary_text", "")
            company_summaries.append({
                "company_id": company.id,
                "company_name": company.name,
                "summary": summary_text or enrichment.response_markdown[:300],
                "total_pipeline_value": structured.get("total_pipeline_value"),
                "opportunity_count": structured.get("opportunity_count", 0),
                "opportunities": structured.get("opportunities", []),
                "fetched_at": enrichment.fetched_at.isoformat() if enrichment.fetched_at else None,
            })
        else:
            company_summaries.append({
                "company_id": company.id,
                "company_name": company.name,
                "summary": enrichment.response_markdown[:300] if enrichment.response_markdown else "",
                "total_pipeline_value": None,
                "opportunity_count": 0,
                "opportunities": [],
                "fetched_at": enrichment.fetched_at.isoformat() if enrichment.fetched_at else None,
            })

    return {
        "available": True,
        "companies_with_data": len(company_summaries),
        "companies": company_summaries,
    }
