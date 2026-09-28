from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.services.relationship_service import (
    get_relationship_summary,
    build_relationship_refresh_prompts,
)

router = APIRouter(prefix="/companies", tags=["relationships"])


@router.get("/{company_id}/relationships")
def get_relationships(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return get_relationship_summary(db, company)


@router.get("/{company_id}/relationships/prompts")
def get_relationship_prompts(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"company_id": company.id, "prompts": build_relationship_refresh_prompts(company)}
