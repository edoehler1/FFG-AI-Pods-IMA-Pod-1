from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch


def match_signals_to_companies(db: Session):
    """Simple name-matching: if a company name appears in a signal's title or body, link them."""
    companies = db.query(Company).all()
    signals = db.query(Signal).all()

    existing = set(
        (r.signal_id, r.company_id)
        for r in db.query(SignalCompanyMatch.signal_id, SignalCompanyMatch.company_id).all()
    )

    new_matches = 0
    for company in companies:
        name_lower = company.name.lower()
        name_parts = [p for p in name_lower.split() if len(p) > 2 and p not in ("inc", "inc.", "ltd", "ltd.", "plc", "corp", "corp.", "the", "and", "company")]

        for signal in signals:
            if (signal.id, company.id) in existing:
                continue

            text = f"{signal.title} {signal.body or ''}".lower()
            if name_lower in text or (len(name_parts) >= 2 and all(p in text for p in name_parts)):
                match = SignalCompanyMatch(
                    signal_id=signal.id,
                    company_id=company.id,
                    match_reason=f"Company name '{company.name}' found in signal text",
                )
                db.add(match)
                existing.add((signal.id, company.id))
                new_matches += 1

    db.commit()
    return new_matches
