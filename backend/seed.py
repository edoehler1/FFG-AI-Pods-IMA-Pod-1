"""
Seed the database with sample companies and contacts.

Usage:
    cd backend && python seed.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.database import Base, engine, SessionLocal
from app.models import Company, Contact, SignalCompanyMatch
from app.services.upload_parser import parse_upload
from app.services.signal_matcher import match_signals_to_companies


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    data_dir = os.path.join(os.path.dirname(__file__), "seed_data")

    with open(os.path.join(data_dir, "sample_companies.csv"), "rb") as f:
        records = parse_upload(f.read(), "sample_companies.csv", "company")

    created = 0
    for record in records:
        existing = db.query(Company).filter(Company.name == record["name"]).first()
        if existing:
            continue
        db.add(Company(**record))
        created += 1
    db.commit()
    print(f"Companies: {created} created, {len(records) - created} already existed")

    with open(os.path.join(data_dir, "sample_contacts.csv"), "rb") as f:
        records = parse_upload(f.read(), "sample_contacts.csv", "contact")

    created = 0
    for record in records:
        company_name = record.pop("company_name", None)
        if company_name:
            company = db.query(Company).filter(Company.name.ilike(f"%{company_name}%")).first()
            if company:
                record["company_id"] = company.id
            else:
                print(f"  Company not found: {company_name}")
                continue

        existing = db.query(Contact).filter(Contact.name == record["name"]).first()
        if existing:
            continue
        db.add(Contact(**record))
        created += 1
    db.commit()
    print(f"Contacts: {created} created")

    new_matches = match_signals_to_companies(db)
    print(f"Signal-company matches: {new_matches} new links created")

    db.close()
    print("\nSeed complete.")


if __name__ == "__main__":
    seed()
