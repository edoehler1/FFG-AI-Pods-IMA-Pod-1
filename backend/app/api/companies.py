from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.contact import Contact
from app.models.engagement import Engagement
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyOut, CompanyListResponse
from app.schemas.contact import ContactOut
from app.schemas.engagement import EngagementOut
from app.schemas.signal import SignalOut

router = APIRouter(prefix="/companies", tags=["companies"])


class CompanyDetailOut(CompanyOut):
    contacts: list[ContactOut] = []
    engagements: list[EngagementOut] = []
    matched_signals: list[SignalOut] = []


@router.get("", response_model=CompanyListResponse)
def list_companies(
    industry: str | None = Query(None),
    sub_sector: str | None = Query(None),
    client_status: str | None = Query(None),
    search: str | None = Query(None, description="Search by company name"),
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

    total = query.count()
    companies = (
        query.order_by(Company.name)
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

    matched_signal_ids = (
        db.query(SignalCompanyMatch.signal_id)
        .filter(SignalCompanyMatch.company_id == company_id)
        .subquery()
    )
    matched_signals = (
        db.query(Signal)
        .filter(Signal.id.in_(matched_signal_ids))
        .order_by(desc(Signal.published_at))
        .limit(20)
        .all()
    )

    return CompanyDetailOut(
        **{c.key: getattr(company, c.key) for c in Company.__table__.columns},
        contacts=company.contacts,
        engagements=company.engagements,
        matched_signals=matched_signals,
    )


@router.post("", response_model=CompanyOut, status_code=201)
def create_company(data: CompanyCreate, db: Session = Depends(get_db)):
    company = Company(**data.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


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
    db.delete(company)
    db.commit()
