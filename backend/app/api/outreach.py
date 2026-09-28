from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.outreach_action import OutreachAction
from app.models.signal_company import SignalCompanyMatch
from app.services.outreach_ranker import rank_outreach

router = APIRouter(prefix="/outreach", tags=["outreach"])

VALID_STATUSES = {"acted_on", "saved", "dismissed"}


class FeedbackBody(BaseModel):
    status: str


@router.get("")
def get_outreach_queue(
    days: int = Query(14, ge=1, le=60),
    limit: int = Query(20, ge=1, le=100),
    show: str = Query("pending", description="Comma-separated statuses: pending, acted_on, saved, dismissed"),
    db: Session = Depends(get_db),
):
    statuses = [s.strip() for s in show.split(",")]
    items = rank_outreach(db, days=days, limit=limit, include_statuses=statuses)
    return {"items": items, "count": len(items), "lookback_days": days}


@router.post("/{match_id}/feedback")
def record_feedback(
    match_id: str,
    body: FeedbackBody,
    db: Session = Depends(get_db),
):
    if body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}",
        )

    match = db.query(SignalCompanyMatch).filter(SignalCompanyMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    existing = (
        db.query(OutreachAction)
        .filter(OutreachAction.signal_company_match_id == match_id)
        .first()
    )

    if existing:
        existing.status = body.status
        existing.updated_at = datetime.utcnow()
    else:
        existing = OutreachAction(
            signal_company_match_id=match_id,
            status=body.status,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)

    return {
        "outreach_id": existing.id,
        "match_id": match_id,
        "status": existing.status,
        "updated_at": (existing.updated_at or existing.created_at).isoformat(),
    }
