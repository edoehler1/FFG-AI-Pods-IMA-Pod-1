import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.schemas.signal import SignalListResponse, SignalOut

router = APIRouter(prefix="/signals", tags=["signals"])


def _normalize_title(title: str) -> str:
    t = title.strip().lower()
    t = re.sub(r'\s*[-–—|]\s*[a-z0-9\s.&]+$', '', t)
    t = re.sub(r'[^a-z0-9\s]', '', t)
    return t[:80]


def _deduplicate(signals: list[Signal]) -> list[Signal]:
    kept: list[Signal] = []
    seen_keys: list[str] = []
    for s in signals:
        key = _normalize_title(s.title)
        is_dupe = False
        for existing_key in seen_keys:
            words_new = set(key.split())
            words_existing = set(existing_key.split())
            if not words_new or not words_existing:
                continue
            overlap = len(words_new & words_existing)
            smaller = min(len(words_new), len(words_existing))
            if smaller > 0 and overlap / smaller >= 0.6:
                is_dupe = True
                break
        if not is_dupe:
            kept.append(s)
            seen_keys.append(key)
    return kept


def _apply_signal_filters(query, industry, sub_sector, signal_type, news_category, source_name, exclude_source, news_scope=None, db=None):
    if industry:
        query = query.filter(Signal.industry == industry)
    if sub_sector:
        query = query.filter(Signal.sub_sector == sub_sector)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if news_category:
        query = query.filter(Signal.news_category == news_category)
    if source_name:
        query = query.filter(Signal.source_name == source_name)
    if exclude_source:
        sources = [s.strip() for s in exclude_source.split(",") if s.strip()]
        if len(sources) == 1:
            query = query.filter(Signal.source_name != sources[0])
        elif sources:
            query = query.filter(~Signal.source_name.in_(sources))
    if news_scope and db:
        name_matched_ids = db.query(SignalCompanyMatch.signal_id).filter(
            SignalCompanyMatch.match_type == "name"
        ).subquery()
        if news_scope == "company":
            query = query.filter(Signal.id.in_(name_matched_ids))
        elif news_scope == "industry":
            query = query.filter(~Signal.id.in_(name_matched_ids))
    return query


def _paginate_signals(query, page, page_size, dedup: bool = True):
    ordered = query.order_by(desc(Signal.published_at))
    if not dedup:
        total = query.count()
        signals = ordered.offset((page - 1) * page_size).limit(page_size).all()
        return SignalListResponse(signals=signals, total=total, page=page, page_size=page_size)

    fetch_limit = max(page * page_size * 3, 200)
    raw = ordered.limit(fetch_limit).all()
    deduped = _deduplicate(raw)
    total = len(deduped)
    start = (page - 1) * page_size
    page_signals = deduped[start : start + page_size]
    return SignalListResponse(signals=page_signals, total=total, page=page, page_size=page_size)


@router.get("", response_model=SignalListResponse)
def list_signals(
    industry: str | None = Query(None, description="Filter by industry: automotive, aerospace_defense, energy"),
    sub_sector: str | None = Query(None, description="Filter by sub-sector: oem, ev, tier1_supplier, defense_prime, upstream, etc."),
    signal_type: str | None = Query(None, description="Filter by type: news, regulatory, earnings, leadership, ma, gov_contract"),
    news_category: str | None = Query(None, description="Filter by category: regulatory, macro, company_moves, trends, general"),
    source_name: str | None = Query(None, description="Filter by source: sec_edgar, federal_register, etc."),
    exclude_source: str | None = Query(None, description="Exclude a source: e.g. sec_edgar"),
    news_scope: str | None = Query(None, description="company = name-matched to a company, industry = not name-matched"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = _apply_signal_filters(db.query(Signal), industry, sub_sector, signal_type, news_category, source_name, exclude_source, news_scope, db)
    return _paginate_signals(query, page, page_size)


@router.get("/portfolio", response_model=SignalListResponse)
def portfolio_signals(
    industry: str | None = Query(None),
    sub_sector: str | None = Query(None),
    signal_type: str | None = Query(None),
    news_category: str | None = Query(None),
    source_name: str | None = Query(None),
    exclude_source: str | None = Query(None),
    news_scope: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    db: Session = Depends(get_db),
):
    active_company_ids = db.query(Company.id).filter(Company.client_status.in_(["active", "past"])).subquery()
    matched_signal_ids = db.query(SignalCompanyMatch.signal_id).filter(SignalCompanyMatch.company_id.in_(active_company_ids)).subquery()
    query = db.query(Signal).filter(Signal.id.in_(matched_signal_ids))
    query = _apply_signal_filters(query, industry, sub_sector, signal_type, news_category, source_name, exclude_source, news_scope, db)
    return _paginate_signals(query, page, page_size)


@router.get("/discovery", response_model=SignalListResponse)
def discovery_signals(
    industry: str | None = Query(None),
    sub_sector: str | None = Query(None),
    signal_type: str | None = Query(None),
    news_category: str | None = Query(None),
    source_name: str | None = Query(None),
    exclude_source: str | None = Query(None),
    news_scope: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    db: Session = Depends(get_db),
):
    active_company_ids = db.query(Company.id).filter(Company.client_status.in_(["active", "past"])).subquery()
    portfolio_signal_ids = db.query(SignalCompanyMatch.signal_id).filter(SignalCompanyMatch.company_id.in_(active_company_ids)).subquery()
    query = db.query(Signal).filter(~Signal.id.in_(portfolio_signal_ids))
    query = _apply_signal_filters(query, industry, sub_sector, signal_type, news_category, source_name, exclude_source, news_scope, db)
    return _paginate_signals(query, page, page_size)


@router.post("/categorize")
def categorize_signals(db: Session = Depends(get_db)):
    from app.services.signal_categorizer import categorize_uncategorized_signals
    count = categorize_uncategorized_signals(db)
    return {"categorized": count}


@router.delete("/cleanup/usaspending")
def delete_usaspending_signals(db: Session = Depends(get_db)):
    usaspending_ids = [
        s.id for s in db.query(Signal.id).filter(Signal.source_name == "usaspending").all()
    ]
    if not usaspending_ids:
        return {"deleted_signals": 0, "deleted_matches": 0}

    match_count = db.query(SignalCompanyMatch).filter(
        SignalCompanyMatch.signal_id.in_(usaspending_ids)
    ).delete(synchronize_session=False)

    signal_count = db.query(Signal).filter(
        Signal.source_name == "usaspending"
    ).delete(synchronize_session=False)

    db.commit()
    return {"deleted_signals": signal_count, "deleted_matches": match_count}


@router.get("/{signal_id}", response_model=SignalOut)
def get_signal(signal_id: str, db: Session = Depends(get_db)):
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal
