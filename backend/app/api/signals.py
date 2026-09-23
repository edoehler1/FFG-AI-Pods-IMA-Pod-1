from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.schemas.signal import SignalListResponse, SignalOut

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=SignalListResponse)
def list_signals(
    industry: str | None = Query(None, description="Filter by industry: automotive, aerospace_defense, energy"),
    sub_sector: str | None = Query(None, description="Filter by sub-sector: oem, ev, tier1_supplier, defense_prime, upstream, etc."),
    signal_type: str | None = Query(None, description="Filter by type: news, regulatory, earnings, leadership, ma, gov_contract"),
    source_name: str | None = Query(None, description="Filter by source: sec_edgar, federal_register, etc."),
    exclude_source: str | None = Query(None, description="Exclude a source: e.g. sec_edgar"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Signal)

    if industry:
        query = query.filter(Signal.industry == industry)
    if sub_sector:
        query = query.filter(Signal.sub_sector == sub_sector)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if source_name:
        query = query.filter(Signal.source_name == source_name)
    if exclude_source:
        query = query.filter(Signal.source_name != exclude_source)

    total = query.count()
    signals = (
        query.order_by(desc(Signal.published_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return SignalListResponse(
        signals=signals,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/portfolio", response_model=SignalListResponse)
def portfolio_signals(
    industry: str | None = Query(None),
    sub_sector: str | None = Query(None),
    signal_type: str | None = Query(None),
    source_name: str | None = Query(None),
    exclude_source: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    active_company_ids = (
        db.query(Company.id)
        .filter(Company.client_status.in_(["active", "past"]))
        .subquery()
    )
    matched_signal_ids = (
        db.query(SignalCompanyMatch.signal_id)
        .filter(SignalCompanyMatch.company_id.in_(active_company_ids))
        .subquery()
    )
    query = db.query(Signal).filter(Signal.id.in_(matched_signal_ids))

    if industry:
        query = query.filter(Signal.industry == industry)
    if sub_sector:
        query = query.filter(Signal.sub_sector == sub_sector)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if source_name:
        query = query.filter(Signal.source_name == source_name)
    if exclude_source:
        query = query.filter(Signal.source_name != exclude_source)

    total = query.count()
    signals = query.order_by(desc(Signal.published_at)).offset((page - 1) * page_size).limit(page_size).all()
    return SignalListResponse(signals=signals, total=total, page=page, page_size=page_size)


@router.get("/discovery", response_model=SignalListResponse)
def discovery_signals(
    industry: str | None = Query(None),
    sub_sector: str | None = Query(None),
    signal_type: str | None = Query(None),
    source_name: str | None = Query(None),
    exclude_source: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    active_company_ids = (
        db.query(Company.id)
        .filter(Company.client_status.in_(["active", "past"]))
        .subquery()
    )
    portfolio_signal_ids = (
        db.query(SignalCompanyMatch.signal_id)
        .filter(SignalCompanyMatch.company_id.in_(active_company_ids))
        .subquery()
    )
    query = db.query(Signal).filter(~Signal.id.in_(portfolio_signal_ids))

    if industry:
        query = query.filter(Signal.industry == industry)
    if sub_sector:
        query = query.filter(Signal.sub_sector == sub_sector)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if source_name:
        query = query.filter(Signal.source_name == source_name)
    if exclude_source:
        query = query.filter(Signal.source_name != exclude_source)

    total = query.count()
    signals = query.order_by(desc(Signal.published_at)).offset((page - 1) * page_size).limit(page_size).all()
    return SignalListResponse(signals=signals, total=total, page=page, page_size=page_size)


@router.get("/{signal_id}", response_model=SignalOut)
def get_signal(signal_id: str, db: Session = Depends(get_db)):
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal
