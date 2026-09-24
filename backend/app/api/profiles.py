from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.company_profile import CompanyProfile
from app.services.profile_builder import build_company_profile

router = APIRouter(prefix="/companies", tags=["profiles"])


@router.get("/{company_id}/profile")
def get_profile(company_id: str, db: Session = Depends(get_db)):
    profile = db.query(CompanyProfile).filter(CompanyProfile.company_id == company_id).first()
    if not profile:
        return {"profile_narrative": None, "generated_at": None}
    return {
        "profile_narrative": profile.profile_narrative,
        "financial_summary": profile.financial_summary,
        "news_summary": profile.news_summary,
        "generated_at": profile.generated_at,
    }


@router.post("/{company_id}/profile/generate")
def generate_profile(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    profile = build_company_profile(db, company)
    return {
        "profile_narrative": profile.profile_narrative,
        "generated_at": profile.generated_at,
    }


@router.post("/profiles/generate-all")
def generate_all_profiles(db: Session = Depends(get_db)):
    companies = db.query(Company).all()
    results = []
    for company in companies:
        try:
            build_company_profile(db, company)
            results.append({"company": company.name, "status": "ok"})
        except Exception as e:
            results.append({"company": company.name, "status": f"error: {e}"})
    return {"generated": len(results), "results": results}
