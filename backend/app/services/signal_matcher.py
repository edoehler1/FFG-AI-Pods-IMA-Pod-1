import re

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch

STOPWORDS = {"inc", "inc.", "ltd", "ltd.", "plc", "corp", "corp.", "the", "and", "company", "corporation", "group", "holdings", "automotive", "technologies", "international", "energy"}

SHORT_NAMES = {
    "Ford Motor Company": ["Ford"],
    "General Motors": ["GM"],
    "Tesla Inc": ["Tesla"],
    "Honda Motor Co": ["Honda"],
    "Rivian Automotive": ["Rivian"],
    "Lucid Group": ["Lucid"],
    "Stellantis NV": ["Stellantis"],
    "Aptiv": ["Aptiv"],
    "Magna International": ["Magna"],
    "Lockheed Martin": ["Lockheed"],
    "Boeing Company": ["Boeing"],
    "RTX Corporation": ["RTX", "Raytheon"],
    "Northrop Grumman": ["Northrop"],
    "General Dynamics": ["General Dynamics"],
    "L3Harris Technologies": ["L3Harris"],
    "Leidos Holdings": ["Leidos"],
    "ExxonMobil": ["Exxon", "ExxonMobil"],
    "Chevron Corporation": ["Chevron"],
    "Shell plc": ["Shell"],
    "ConocoPhillips": ["ConocoPhillips", "Conoco"],
    "NextEra Energy": ["NextEra"],
    "Duke Energy": ["Duke Energy"],
    "Dominion Energy": ["Dominion Energy"],
    "Southern Company": ["Southern Company"],
    "AES Corporation": ["AES"],
    "Enbridge Inc": ["Enbridge"],
}


def match_signals_to_companies(db: Session):
    companies = db.query(Company).all()
    signals = db.query(Signal).all()

    existing = set(
        (r.signal_id, r.company_id)
        for r in db.query(SignalCompanyMatch.signal_id, SignalCompanyMatch.company_id).all()
    )

    new_matches = 0
    for company in companies:
        search_terms = SHORT_NAMES.get(company.name, [])
        if not search_terms:
            name_parts = [p for p in company.name.split() if p.lower() not in STOPWORDS and len(p) > 2]
            if name_parts:
                search_terms = [company.name] + ([name_parts[0]] if len(name_parts[0]) > 3 else [])

        for signal in signals:
            if (signal.id, company.id) in existing:
                continue

            text = f"{signal.title} {signal.body or ''}".lower()

            matched = False
            for term in search_terms:
                if re.search(r'\b' + re.escape(term.lower()) + r'\b', text):
                    matched = True
                    break

            if matched:
                match = SignalCompanyMatch(
                    signal_id=signal.id,
                    company_id=company.id,
                    match_reason=f"'{search_terms[0]}' found in signal text",
                )
                db.add(match)
                existing.add((signal.id, company.id))
                new_matches += 1

    db.commit()
    return new_matches
