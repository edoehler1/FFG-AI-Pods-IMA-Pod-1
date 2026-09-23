from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.engagement import Engagement
from app.schemas.engagement import EngagementCreate, EngagementOut, EngagementListResponse

router = APIRouter(tags=["engagements"])


@router.get("/companies/{company_id}/engagements", response_model=EngagementListResponse)
def list_engagements(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    engagements = db.query(Engagement).filter(Engagement.company_id == company_id).all()
    return EngagementListResponse(engagements=engagements, total=len(engagements))


@router.post("/companies/{company_id}/engagements", response_model=EngagementOut, status_code=201)
def create_engagement(company_id: str, data: EngagementCreate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    engagement = Engagement(company_id=company_id, **data.model_dump())
    db.add(engagement)
    db.commit()
    db.refresh(engagement)
    return engagement
