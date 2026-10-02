import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.curated_news_cache import CuratedNewsCache
from app.services.industry_news_curator import curate_industry_news

router = APIRouter(prefix="/industries", tags=["industries"])

VALID_INDUSTRIES = {"automotive", "aerospace_defense", "energy"}


def _current_week_start(now=None):
    if now is None:
        now = datetime.utcnow()
    days_since_sunday = (now.weekday() + 1) % 7
    sunday = now - timedelta(days=days_since_sunday)
    return sunday.strftime("%Y-%m-%d")


@router.get("/{industry}/curated-news")
def get_industry_curated_news(
    industry: str,
    days: int = Query(7, ge=1, le=90),
    refresh: bool = Query(False, description="Force regeneration"),
    db: Session = Depends(get_db),
):
    if industry not in VALID_INDUSTRIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown industry: {industry}. Valid: {sorted(VALID_INDUSTRIES)}",
        )

    now = datetime.utcnow()
    week_start = _current_week_start(now)

    if not refresh:
        cached = (
            db.query(CuratedNewsCache)
            .filter(
                CuratedNewsCache.scope == "industry",
                CuratedNewsCache.scope_id == industry,
                CuratedNewsCache.week_start == week_start,
            )
            .first()
        )
        if cached:
            return {
                "industry": industry,
                "curated_news": json.loads(cached.curated_json),
                "date_range": {
                    "start": (now - timedelta(days=days)).isoformat(),
                    "end": now.isoformat(),
                },
                "cached": True,
                "generated_at": cached.generated_at.isoformat(),
            }

    curated = curate_industry_news(db, industry, days_back=days)

    existing = (
        db.query(CuratedNewsCache)
        .filter(
            CuratedNewsCache.scope == "industry",
            CuratedNewsCache.scope_id == industry,
            CuratedNewsCache.week_start == week_start,
        )
        .first()
    )
    if existing:
        existing.curated_json = json.dumps(curated)
        existing.generated_at = now
    else:
        db.add(CuratedNewsCache(
            scope="industry",
            scope_id=industry,
            week_start=week_start,
            curated_json=json.dumps(curated),
            generated_at=now,
        ))
    db.commit()

    return {
        "industry": industry,
        "curated_news": curated,
        "date_range": {
            "start": (now - timedelta(days=days)).isoformat(),
            "end": now.isoformat(),
        },
        "cached": False,
        "generated_at": now.isoformat(),
    }
