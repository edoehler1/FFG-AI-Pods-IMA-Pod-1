from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.benchmark_builder import (
    generate_all_benchmarks,
    generate_and_store_benchmark,
    get_benchmark,
    SECTOR_COMPANIES,
)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("/{industry}")
def get_industry_benchmark(industry: str, db: Session = Depends(get_db)):
    if industry not in SECTOR_COMPANIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown industry: {industry}. Valid: {list(SECTOR_COMPANIES.keys())}",
        )
    data = get_benchmark(db, industry)
    if not data:
        raise HTTPException(status_code=404, detail=f"No benchmark for {industry}. Run POST /api/benchmarks/generate first.")
    return data


@router.post("/generate")
def generate_benchmarks(db: Session = Depends(get_db)):
    results = generate_all_benchmarks(db)
    return {"results": results}


@router.post("/generate/{industry}")
def generate_single_benchmark(industry: str, db: Session = Depends(get_db)):
    if industry not in SECTOR_COMPANIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown industry: {industry}. Valid: {list(SECTOR_COMPANIES.keys())}",
        )
    record = generate_and_store_benchmark(db, industry)
    return {"industry": industry, "status": "ok", "generated_at": record.generated_at}
