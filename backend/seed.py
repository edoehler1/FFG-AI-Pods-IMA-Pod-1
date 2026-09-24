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
from app.services.relevance_scorer import passes_blocklist, score_articles_with_claude


# Ambiguous short names that need industry context to match
AMBIGUOUS_NAMES = {"Ford", "Shell", "Magna", "AES", "GM"}

SHORT_NAMES = {
    "Ford Motor Company": ["Ford Motor", "Ford"], "General Motors": ["General Motors", "GM"],
    "Tesla Inc": ["Tesla"], "Honda Motor Co": ["Honda"],
    "Rivian Automotive": ["Rivian"], "Lucid Group": ["Lucid Motors", "Lucid Group"],
    "Stellantis NV": ["Stellantis"], "Aptiv": ["Aptiv"],
    "Magna International": ["Magna International", "Magna"],
    "Bosch": ["Bosch"],
    "Lockheed Martin": ["Lockheed Martin", "Lockheed"], "Boeing Company": ["Boeing"],
    "RTX Corporation": ["RTX", "Raytheon"], "Northrop Grumman": ["Northrop Grumman", "Northrop"],
    "General Dynamics": ["General Dynamics"], "L3Harris Technologies": ["L3Harris"],
    "Leidos Holdings": ["Leidos"], "ExxonMobil": ["ExxonMobil", "Exxon"],
    "Chevron Corporation": ["Chevron"], "Shell plc": ["Shell plc", "Shell"],
    "ConocoPhillips": ["ConocoPhillips"], "NextEra Energy": ["NextEra"],
    "Duke Energy": ["Duke Energy"], "Dominion Energy": ["Dominion Energy"],
    "Southern Company": ["Southern Company"], "AES Corporation": ["AES Corporation", "AES"],
    "Enbridge Inc": ["Enbridge"],
}


def _fast_name_match(db):
    companies = db.query(Company).all()
    signals = db.query(Signal).all()
    existing = set(
        (r.signal_id, r.company_id)
        for r in db.query(SignalCompanyMatch.signal_id, SignalCompanyMatch.company_id).all()
    )

    # Stage 1: Name match + blocklist filter
    candidates_by_company: dict[str, list[tuple]] = {}
    for company in companies:
        terms = SHORT_NAMES.get(company.name, [company.name])
        candidates = []
        for signal in signals:
            if (signal.id, company.id) in existing:
                continue
            text = f"{signal.title} {signal.body or ''}".lower()

            matched_term = None
            for term in terms:
                if re.search(r"\b" + re.escape(term.lower()) + r"\b", text):
                    matched_term = term
                    break
            if not matched_term:
                continue

            score = _compute_match_score(signal, company, matched_term)
            if score < 0.5:
                continue

            # SEC filings always pass
            if signal.source_name == "sec_edgar":
                candidates.append((signal, matched_term, score, "SEC filing"))
                continue

            # Blocklist check for news
            if not passes_blocklist(signal.title, signal.body, signal.signal_type):
                continue

            candidates.append((signal, matched_term, score, None))

        candidates_by_company[company.id] = candidates

    # Stage 2: Claude scoring for news articles (batch per company)
    new = 0
    for company in companies:
        candidates = candidates_by_company.get(company.id, [])
        sec_filings = [(s, t, sc, r) for s, t, sc, r in candidates if s.source_name == "sec_edgar"]
        news_articles = [(s, t, sc, r) for s, t, sc, r in candidates if s.source_name != "sec_edgar"]

        # SEC filings go straight in
        for signal, term, score, reason in sec_filings:
            db.add(SignalCompanyMatch(
                signal_id=signal.id, company_id=company.id,
                match_type="name", match_score=score,
                match_reason=reason or f"{term} found",
            ))
            existing.add((signal.id, company.id))
            new += 1

        # News articles get Claude scored
        if news_articles:
            articles_for_claude = [
                {"index": i, "title": s.title, "body": s.body, "signal_type": s.signal_type}
                for i, (s, _, _, _) in enumerate(news_articles)
            ]

            # Batch in groups of 15
            for batch_start in range(0, len(articles_for_claude), 15):
                batch = articles_for_claude[batch_start:batch_start + 15]
                scores = score_articles_with_claude(batch, company.name, company.industry)

                score_map = {r["index"]: r for r in scores}
                for i, (signal, term, _, _) in enumerate(news_articles[batch_start:batch_start + 15]):
                    result = score_map.get(batch_start + i, {})
                    claude_score = result.get("score", 50)
                    reason = result.get("reason", f"{term} found")
                    is_dupe = result.get("is_duplicate", False)

                    if claude_score < 50 or is_dupe:
                        continue

                    db.add(SignalCompanyMatch(
                        signal_id=signal.id, company_id=company.id,
                        match_type="name", match_score=claude_score / 100.0,
                        match_reason=reason,
                    ))
                    existing.add((signal.id, company.id))
                    new += 1

    db.commit()
    return new


def _compute_match_score(signal, company, matched_term: str) -> float:
    score = 0.5

    # Full name or multi-word match = high confidence
    if len(matched_term.split()) >= 2:
        score = 0.9

    # Single ambiguous word = needs strong business context
    if matched_term in AMBIGUOUS_NAMES:
        score = 0.0
        text = f"{signal.title} {signal.body or ''}".lower()
        business_words = ["earnings", "stock", "revenue", "ceo", "quarterly", "shares",
                          "profit", "investor", "market cap", "analyst", "dividend"]
        industry_words = {
            "automotive": ["car", "vehicle", "auto", "ev", "dealer", "suv", "truck", "motor", "driving", "automaker"],
            "aerospace_defense": ["defense", "military", "aircraft", "missile", "pentagon", "contract", "fighter"],
            "energy": ["oil", "gas", "energy", "pipeline", "refinery", "drilling", "power", "barrel"],
        }
        context_words = industry_words.get(company.industry or "", [])
        has_industry_context = any(w in text for w in context_words)
        has_business_context = any(w in text for w in business_words)
        if has_industry_context and has_business_context:
            score = 0.9
        elif has_industry_context:
            score = 0.7
        elif has_business_context:
            score = 0.6
        if signal.source_name == "sec_edgar":
            score = 0.95
    else:
        # Non-ambiguous single word (Tesla, Boeing, Chevron, etc.)
        if company.industry and signal.industry and company.industry == signal.industry:
            score = 0.9
        elif signal.industry:
            score = 0.6

    # SEC filings with company name in title are always high confidence
    if signal.source_name == "sec_edgar" and company.name.lower() in signal.title.lower():
        score = 1.0

    return score


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
