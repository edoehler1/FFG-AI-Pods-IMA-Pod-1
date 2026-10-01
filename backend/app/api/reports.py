import json

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.weekly_report import WeeklyReport
from app.services.report_generator import gather_report_data, generate_report_with_llm
from app.services.portfolio_report_builder import generate_portfolio_report, get_saved_reports, get_saved_report
from app.services.weekly_briefing_builder import build_weekly_briefing

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportResponse(BaseModel):
    markdown: str
    company_count: int
    total_matched_signals: int
    period_days: int
    period_start: str | None = None
    period_end: str | None = None


@router.post("/generate", response_model=ReportResponse)
def generate_report(
    industry: str | None = Query(None),
    client_status: str | None = Query(None),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    report_data = gather_report_data(db, industry=industry, client_status=client_status, days=days)
    markdown = generate_report_with_llm(report_data)

    return ReportResponse(
        markdown=markdown,
        company_count=report_data["company_count"],
        total_matched_signals=report_data["total_matched_signals"],
        period_days=report_data["period_days"],
        period_start=report_data.get("period_start"),
        period_end=report_data.get("period_end"),
    )


@router.post("/weekly/generate")
def generate_weekly_reports(
    days_back: int = Query(7, ge=1, le=30),
    body: dict | None = None,
    db: Session = Depends(get_db),
):
    from app.services.weekly_report_agent import generate_weekly_reports
    company_ids = body.get("company_ids") if body else None
    results = generate_weekly_reports(db, days_back=days_back, company_ids=company_ids)
    opportunities = sum(1 for r in results if r.get("has_opportunity"))
    reports_created = sum(1 for r in results if r["status"] in ("generated", "already_generated"))
    return {
        "total_companies": len(results),
        "reports_created": reports_created,
        "opportunities_found": opportunities,
        "results": results,
    }


@router.get("/weekly/summary")
def list_weekly_report_summaries(
    company_id: str | None = Query(None),
    has_opportunity: bool | None = Query(None),
    urgency: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(WeeklyReport)
    if company_id:
        query = query.filter(WeeklyReport.company_id == company_id)
    if has_opportunity is not None:
        query = query.filter(WeeklyReport.has_opportunity == has_opportunity)
    if urgency:
        query = query.filter(WeeklyReport.urgency == urgency)

    reports = query.order_by(desc(WeeklyReport.generated_at)).limit(limit).all()

    results = []
    for r in reports:
        company = db.query(Company).filter(Company.id == r.company_id).first()
        results.append({
            "id": r.id,
            "company_id": r.company_id,
            "company_name": company.name if company else "Unknown",
            "week_start": r.week_start,
            "week_end": r.week_end,
            "signal_count": r.signal_count,
            "has_opportunity": r.has_opportunity,
            "urgency": r.urgency,
            "opportunity_summary": r.opportunity_summary,
            "suggested_lead": r.suggested_lead,
            "top_signal_title": r.top_signal_title,
            "generated_at": r.generated_at,
        })

    return {"reports": results, "total": len(results)}


@router.get("/weekly")
def list_weekly_reports(
    company_id: str | None = Query(None),
    has_opportunity: bool | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(WeeklyReport)
    if company_id:
        query = query.filter(WeeklyReport.company_id == company_id)
    if has_opportunity is not None:
        query = query.filter(WeeklyReport.has_opportunity == has_opportunity)

    reports = query.order_by(desc(WeeklyReport.generated_at)).limit(limit).all()

    results = []
    for r in reports:
        company = db.query(Company).filter(Company.id == r.company_id).first()
        results.append({
            "id": r.id,
            "company_id": r.company_id,
            "company_name": company.name if company else "Unknown",
            "week_start": r.week_start,
            "week_end": r.week_end,
            "content": r.content,
            "signal_count": r.signal_count,
            "has_opportunity": r.has_opportunity,
            "urgency": r.urgency,
            "opportunity_summary": r.opportunity_summary,
            "suggested_lead": r.suggested_lead,
            "financial_cross_ref": r.financial_cross_ref,
            "top_signal_title": r.top_signal_title,
            "generated_at": r.generated_at,
        })

    return {"reports": results, "total": len(results)}


@router.get("/weekly/{report_id}")
def get_weekly_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(WeeklyReport).filter(WeeklyReport.id == report_id).first()
    if not report:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Report not found")

    company = db.query(Company).filter(Company.id == report.company_id).first()
    return {
        "id": report.id,
        "company_id": report.company_id,
        "company_name": company.name if company else "Unknown",
        "week_start": report.week_start,
        "week_end": report.week_end,
        "content": report.content,
        "signal_count": report.signal_count,
        "has_opportunity": report.has_opportunity,
        "urgency": report.urgency,
        "opportunity_summary": report.opportunity_summary,
        "suggested_lead": report.suggested_lead,
        "financial_cross_ref": report.financial_cross_ref,
        "top_signal_title": report.top_signal_title,
        "generated_at": report.generated_at,
    }


class PortfolioRequest(BaseModel):
    company_ids: list[str]
    days_back: int = 7


@router.post("/portfolio/generate")
def generate_portfolio(body: PortfolioRequest, db: Session = Depends(get_db)):
    if not body.company_ids:
        return {"cards": [], "themes": [], "actions": [], "company_count": 0, "industries": []}
    result = generate_portfolio_report(db, body.company_ids, body.days_back)
    return result


@router.get("/portfolio/saved")
def list_saved_portfolios(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return {"reports": get_saved_reports(db, limit)}


@router.get("/portfolio/saved/{report_id}")
def get_saved_portfolio(report_id: str, db: Session = Depends(get_db)):
    result = get_saved_report(db, report_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Report not found")
    return result


class BriefingRequest(BaseModel):
    company_id: str
    days_back: int = 7


@router.post("/briefing/generate")
def generate_briefing(body: BriefingRequest, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == body.company_id).first()
    if not company:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Company not found")
    result = build_weekly_briefing(db, company, days_back=body.days_back)
    return result


@router.get("/briefing/{company_id}")
def get_latest_briefing(company_id: str, db: Session = Depends(get_db)):
    report = (
        db.query(WeeklyReport)
        .filter(WeeklyReport.company_id == company_id)
        .order_by(desc(WeeklyReport.generated_at))
        .first()
    )
    if not report:
        return {"card": None, "full_report": None}

    card = None
    if report.opportunity_summary:
        try:
            card = json.loads(report.opportunity_summary)
        except (json.JSONDecodeError, TypeError):
            pass

    company = db.query(Company).filter(Company.id == company_id).first()
    return {
        "card": card,
        "full_report": report.content,
        "company_id": report.company_id,
        "company_name": company.name if company else "Unknown",
        "week_start": report.week_start,
        "week_end": report.week_end,
        "signal_count": report.signal_count,
        "generated_at": report.generated_at,
        "report_id": report.id,
    }
