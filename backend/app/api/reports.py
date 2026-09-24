from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.weekly_report import WeeklyReport
from app.services.report_generator import gather_report_data, generate_report_with_llm

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportResponse(BaseModel):
    markdown: str
    company_count: int
    total_matched_signals: int
    period_days: int


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
    )


@router.post("/weekly/generate")
def generate_weekly_reports(
    days_back: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    from app.services.weekly_report_agent import generate_weekly_reports
    results = generate_weekly_reports(db, days_back=days_back)
    opportunities = sum(1 for r in results if r.get("has_opportunity"))
    return {
        "total_companies": len(results),
        "opportunities_found": opportunities,
        "results": results,
    }


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
        "company_name": company.name if company else "Unknown",
        "week_start": report.week_start,
        "week_end": report.week_end,
        "content": report.content,
        "signal_count": report.signal_count,
        "has_opportunity": report.has_opportunity,
        "generated_at": report.generated_at,
    }
