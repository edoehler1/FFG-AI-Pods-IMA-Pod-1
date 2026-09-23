from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.contact import Contact
from app.services.upload_parser import parse_upload

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/companies")
async def upload_companies(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    try:
        records = parse_upload(content, file.filename, "company")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not records:
        raise HTTPException(status_code=400, detail="No valid records found. Check that your file has a header row with a 'Name' or 'Company' column.")

    created = 0
    skipped = 0
    for record in records:
        existing = db.query(Company).filter(Company.name == record["name"]).first()
        if existing:
            skipped += 1
            continue
        company = Company(**record)
        db.add(company)
        created += 1

    db.commit()
    return {"created": created, "skipped": skipped, "total_in_file": len(records)}


@router.post("/contacts")
async def upload_contacts(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    try:
        records = parse_upload(content, file.filename, "contact")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not records:
        raise HTTPException(status_code=400, detail="No valid records found. Check that your file has a header row with 'Name' and 'Company' columns.")

    created = 0
    skipped = 0
    not_found = 0
    for record in records:
        company_name = record.pop("company_name", None)
        if company_name:
            company = db.query(Company).filter(Company.name.ilike(f"%{company_name}%")).first()
            if company:
                record["company_id"] = company.id
            else:
                not_found += 1
                continue
        else:
            skipped += 1
            continue

        contact = Contact(**record)
        db.add(contact)
        created += 1

    db.commit()
    return {"created": created, "skipped": skipped, "company_not_found": not_found, "total_in_file": len(records)}
