"""
Seed the database with sample companies and contacts.

Usage:
    cd backend && python seed.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.database import Base, engine, SessionLocal
from app.models import Company, Contact, SignalCompanyMatch
from app.models.signal import Signal
from app.services.upload_parser import parse_upload


SHORT_NAMES = {
    "Ford Motor Company": ["Ford"], "General Motors": ["GM"], "Tesla Inc": ["Tesla"],
    "Honda Motor Co": ["Honda"], "Rivian Automotive": ["Rivian"], "Lucid Group": ["Lucid"],
    "Stellantis NV": ["Stellantis"], "Aptiv": ["Aptiv"], "Magna International": ["Magna"],
    "Lockheed Martin": ["Lockheed"], "Boeing Company": ["Boeing"],
    "RTX Corporation": ["RTX", "Raytheon"], "Northrop Grumman": ["Northrop"],
    "General Dynamics": ["General Dynamics"], "L3Harris Technologies": ["L3Harris"],
    "Leidos Holdings": ["Leidos"], "ExxonMobil": ["Exxon", "ExxonMobil"],
    "Chevron Corporation": ["Chevron"], "Shell plc": ["Shell"],
    "ConocoPhillips": ["ConocoPhillips"], "NextEra Energy": ["NextEra"],
    "Duke Energy": ["Duke Energy"], "Dominion Energy": ["Dominion Energy"],
    "Southern Company": ["Southern Company"], "AES Corporation": ["AES"],
    "Enbridge Inc": ["Enbridge"],
}


def _fast_name_match(db):
    companies = db.query(Company).all()
    signals = db.query(Signal).all()
    existing = set(
        (r.signal_id, r.company_id)
        for r in db.query(SignalCompanyMatch.signal_id, SignalCompanyMatch.company_id).all()
    )
    new = 0
    for company in companies:
        terms = SHORT_NAMES.get(company.name, [company.name])
        for signal in signals:
            if (signal.id, company.id) in existing:
                continue
            text = f"{signal.title} {signal.body or ''}".lower()
            for term in terms:
                if re.search(r"\b" + re.escape(term.lower()) + r"\b", text):
                    db.add(SignalCompanyMatch(signal_id=signal.id, company_id=company.id, match_type="name", match_score=1.0, match_reason=f"{term} found"))
                    existing.add((signal.id, company.id))
                    new += 1
                    break
    db.commit()
    return new


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

    new_matches = _fast_name_match(db)
    print(f"Signal-company matches: {new_matches} new links created")

    db.close()
    print("\nSeed complete.")


if __name__ == "__main__":
    seed()
