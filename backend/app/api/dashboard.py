import json
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.weekly_report import WeeklyReport

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(db: Session = Depends(get_db)):
    companies = db.query(Company).order_by(Company.name).all()

    briefing_cards = []
    no_briefing = []

    for company in companies:
        report = (
            db.query(WeeklyReport)
            .filter(WeeklyReport.company_id == company.id)
            .order_by(desc(WeeklyReport.generated_at))
            .first()
        )

        card_data = None
        if report and report.opportunity_summary:
            try:
                card_data = json.loads(report.opportunity_summary)
            except (json.JSONDecodeError, TypeError):
                pass

        if card_data and card_data.get("headline"):
            briefing_cards.append({
                "company_id": company.id,
                "company_name": company.name,
                "industry": company.industry,
                "client_status": company.client_status,
                "headline": card_data.get("headline", ""),
                "confidence_score": card_data.get("confidence_score", 0),
                "confidence_tier": card_data.get("confidence_tier", "Noted"),
                "opportunity": card_data.get("opportunity", ""),
                "taxonomy_tag": card_data.get("taxonomy_tag", ""),
                "action": card_data.get("action", ""),
                "week_start": report.week_start,
                "week_end": report.week_end,
                "generated_at": report.generated_at.isoformat() if report.generated_at else None,
            })
        else:
            no_briefing.append({
                "company_id": company.id,
                "company_name": company.name,
                "industry": company.industry,
                "client_status": company.client_status,
            })

    briefing_cards.sort(key=lambda c: c["confidence_score"], reverse=True)

    return {
        "briefing_cards": briefing_cards,
        "companies_without_briefings": no_briefing,
        "generated_at": datetime.utcnow().isoformat(),
    }
