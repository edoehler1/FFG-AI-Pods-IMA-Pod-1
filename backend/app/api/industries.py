from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.industry_news_curator import curate_industry_news

router = APIRouter(prefix="/industries", tags=["industries"])

VALID_INDUSTRIES = {"automotive", "aerospace_defense", "energy"}


@router.get("/{industry}/curated-news")
def get_industry_curated_news(
    industry: str,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    if industry not in VALID_INDUSTRIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown industry: {industry}. Valid: {sorted(VALID_INDUSTRIES)}",
        )

    curated = curate_industry_news(db, industry, days_back=days)
    now = datetime.utcnow()
    return {
        "industry": industry,
        "curated_news": curated,
        "date_range": {
            "start": (now - timedelta(days=days)).isoformat(),
            "end": now.isoformat(),
        },
    }
