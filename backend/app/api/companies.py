from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.company_analysis import CompanyAnalysis
from app.models.company_profile import CompanyProfile
from app.models.contact import Contact
from app.models.engagement import Engagement
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.models.weekly_report import WeeklyReport
from app.models.mcp_enrichment import MCPEnrichment
from app.models.outreach_action import OutreachAction
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyOut, CompanyListResponse
from app.schemas.contact import ContactOut
from app.schemas.engagement import EngagementOut
from app.schemas.signal import SignalOut, MatchedSignalOut
from app.services.company_analyzer import get_company_intelligence, generate_company_analysis
from app.services.financial_analyzer import generate_financial_analysis

router = APIRouter(prefix="/companies", tags=["companies"])


class CompanyDetailOut(CompanyOut):
    contacts: list[ContactOut] = []
    engagements: list[EngagementOut] = []
    matched_signals: list[MatchedSignalOut] = []


COMPANY_SORT_COLUMNS = {
    "name": Company.name,
    "industry": Company.industry,
    "client_status": Company.client_status,
    "created_at": Company.created_at,
}


@router.get("", response_model=CompanyListResponse)
def list_companies(
    industry: str | None = Query(None),
    sub_sector: str | None = Query(None),
    client_status: str | None = Query(None),
    search: str | None = Query(None, description="Search by company name"),
    sort_by: str = Query("name", description="Sort field: name, industry, client_status, created_at"),
    sort_order: str = Query("asc", description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Company)
    if industry:
        query = query.filter(Company.industry == industry)
    if sub_sector:
        query = query.filter(Company.sub_sector == sub_sector)
    if client_status:
        query = query.filter(Company.client_status == client_status)
    if search:
        query = query.filter(Company.name.ilike(f"%{search}%"))

    sort_col = COMPANY_SORT_COLUMNS.get(sort_by, Company.name)
    order_clause = desc(sort_col) if sort_order == "desc" else sort_col

    total = query.count()
    companies = (
        query.order_by(order_clause)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return CompanyListResponse(companies=companies, total=total, page=page, page_size=page_size)


@router.get("/{company_id}", response_model=CompanyDetailOut)
def get_company(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    matches_with_signals = (
        db.query(SignalCompanyMatch, Signal)
        .join(Signal, Signal.id == SignalCompanyMatch.signal_id)
        .filter(SignalCompanyMatch.company_id == company_id)
        .order_by(desc(Signal.published_at))
        .limit(20)
        .all()
    )

    matched_signals = [
        MatchedSignalOut(
            signal=SignalOut.model_validate(signal),
            match_score=match.match_score,
            match_type=match.match_type,
            match_reason=match.match_reason,
            talking_points=match.talking_points,
        )
        for match, signal in matches_with_signals
    ]

    return CompanyDetailOut(
        **{c.key: getattr(company, c.key) for c in Company.__table__.columns},
        contacts=company.contacts,
        engagements=company.engagements,
        matched_signals=matched_signals,
    )


@router.get("/{company_id}/matches", response_model=list[MatchedSignalOut])
def get_company_matches(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    matches_with_signals = (
        db.query(SignalCompanyMatch, Signal)
        .join(Signal, Signal.id == SignalCompanyMatch.signal_id)
        .filter(SignalCompanyMatch.company_id == company_id)
        .order_by(desc(SignalCompanyMatch.match_score))
        .all()
    )

    return [
        MatchedSignalOut(
            signal=SignalOut.model_validate(signal),
            match_score=match.match_score,
            match_type=match.match_type,
            match_reason=match.match_reason,
            talking_points=match.talking_points,
        )
        for match, signal in matches_with_signals
    ]


@router.post("", response_model=CompanyOut, status_code=201)
def create_company(data: CompanyCreate, db: Session = Depends(get_db)):
    company = Company(**data.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)

    try:
        from threading import Thread
        Thread(target=_onboard_in_background, args=(company.id,), daemon=True).start()
    except Exception as e:
        print(f"Failed to start onboarding thread for {company.name}: {e}")

    return company


def _onboard_in_background(company_id: str):
    from app.database import SessionLocal
    from app.models.company import Company as Co
    from app.services.onboarding import onboard_company
    db = SessionLocal()
    try:
        company = db.query(Co).filter(Co.id == company_id).first()
        if company:
            result = onboard_company(db, company)
            print(f"Onboarded {company.name}: {result}")
    except Exception as e:
        print(f"Onboarding failed: {e}")
    finally:
        db.close()


@router.put("/{company_id}", response_model=CompanyOut)
def update_company(company_id: str, data: CompanyUpdate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(company, field, value)

    db.commit()
    db.refresh(company)
    return company


@router.delete("/{company_id}", status_code=204)
def delete_company(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    match_ids = [m.id for m in db.query(SignalCompanyMatch.id).filter(SignalCompanyMatch.company_id == company_id).all()]
    if match_ids:
        db.query(OutreachAction).filter(OutreachAction.signal_company_match_id.in_(match_ids)).delete(synchronize_session=False)
    db.query(SignalCompanyMatch).filter(SignalCompanyMatch.company_id == company_id).delete(synchronize_session=False)
    db.query(WeeklyReport).filter(WeeklyReport.company_id == company_id).delete(synchronize_session=False)
    db.query(CompanyAnalysis).filter(CompanyAnalysis.company_id == company_id).delete(synchronize_session=False)
    db.query(CompanyProfile).filter(CompanyProfile.company_id == company_id).delete(synchronize_session=False)
    db.query(MCPEnrichment).filter(
        MCPEnrichment.entity_type == "company",
        MCPEnrichment.entity_id == company_id,
    ).delete(synchronize_session=False)
    db.delete(company)
    db.commit()


@router.get("/{company_id}/intelligence")
def get_intelligence(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    intel = get_company_intelligence(db, company)
    categories = intel.get("industry_news_categories", {})
    industry_signals = []
    for s in intel["industry_news"]:
        out = SignalOut.model_validate(s).model_dump()
        out["news_category"] = categories.get(s.id, "general")
        industry_signals.append(out)
    return {
        "filings": [SignalOut.model_validate(s) for s in intel["filings"]],
        "company_news": [SignalOut.model_validate(s) for s in intel["company_news"]],
        "industry_news": industry_signals,
    }


@router.get("/{company_id}/analysis")
def get_analysis(company_id: str, db: Session = Depends(get_db)):
    analysis = db.query(CompanyAnalysis).filter(CompanyAnalysis.company_id == company_id).first()
    if not analysis:
        return {"narrative": None, "generated_at": None}
    return {
        "narrative": analysis.narrative,
        "signal_count": analysis.signal_count,
        "filing_count": analysis.filing_count,
        "generated_at": analysis.generated_at,
    }


@router.post("/{company_id}/analyze")
def trigger_analysis(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    analysis = generate_company_analysis(db, company)
    return {
        "narrative": analysis.narrative,
        "signal_count": analysis.signal_count,
        "filing_count": analysis.filing_count,
        "generated_at": analysis.generated_at,
    }


@router.post("/{company_id}/financial-analysis")
def trigger_financial_analysis(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    narrative = generate_financial_analysis(db, company)
    return {"narrative": narrative}


@router.post("/analysis/refresh-all")
def refresh_all_analyses(db: Session = Depends(get_db)):
    companies = db.query(Company).all()
    results = []
    for company in companies:
        try:
            analysis = generate_company_analysis(db, company)
            results.append({"company": company.name, "status": "ok"})
        except Exception as e:
            results.append({"company": company.name, "status": f"error: {e}"})
    return {"refreshed": len(results), "results": results}
