from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.signal import Signal
from app.schemas.signal import SignalListResponse, SignalOut

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=SignalListResponse)
def list_signals(
    industry: str | None = Query(None, description="Filter by industry: automotive, aerospace_defense"),
    signal_type: str | None = Query(None, description="Filter by type: news, regulatory, earnings, leadership, ma, gov_contract"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Signal)

    if industry:
        query = query.filter(Signal.industry == industry)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)

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


@router.get("/{signal_id}", response_model=SignalOut)
def get_signal(signal_id: str, db: Session = Depends(get_db)):
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal
