from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
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
