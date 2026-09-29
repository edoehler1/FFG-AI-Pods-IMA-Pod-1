"""
Seed the database with sample companies and contacts.

Usage:
    cd backend && python seed.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base, engine, SessionLocal
from app.models import Company, Contact, SignalCompanyMatch
from app.models.signal import Signal
from app.services.upload_parser import parse_upload
from app.services.relevance_scorer import passes_blocklist, score_articles_with_claude
from app.services.signal_matcher import SHORT_NAMES, AMBIGUOUS_NAMES, compute_match_score


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

            score = compute_match_score(signal, company, matched_term)
            if score < 0.5:
                continue

            # SEC filings always pass
            if signal.source_name == "sec_edgar":
                candidates.append((signal, matched_term, score, "SEC filing"))
                continue

            # Blocklist check for news
            if not passes_blocklist(signal.title, signal.body, signal.signal_type, signal.source_name, signal.url):
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

    _seed_enrichments(db, data_dir)

    db.close()
    print("\nSeed complete.")


def _seed_enrichments(db, data_dir: str):
    import json
    import uuid
    from datetime import datetime, timedelta
    from app.models.mcp_enrichment import MCPEnrichment

    enrichment_file = os.path.join(data_dir, "people_connector_enrichments.json")
    if not os.path.exists(enrichment_file):
        print("Enrichments: no seed file found, skipping")
        return

    with open(enrichment_file) as f:
        records = json.load(f)

    created = 0
    skipped = 0
    now = datetime.utcnow()

    for record in records:
        company = db.query(Company).filter(Company.name == record["company_name"]).first()
        if not company:
            print(f"  Enrichment skipped: company '{record['company_name']}' not found")
            skipped += 1
            continue

        existing = db.query(MCPEnrichment).filter(
            MCPEnrichment.entity_type == "company",
            MCPEnrichment.entity_id == company.id,
            MCPEnrichment.mcp_source == "people_engagements",
        ).first()

        if existing:
            skipped += 1
            continue

        db.add(MCPEnrichment(
            id=str(uuid.uuid4()),
            entity_type="company",
            entity_id=company.id,
            mcp_source="people_engagements",
            query_prompt=record.get("query_prompt", ""),
            response_markdown=record.get("response_markdown", ""),
            response_summary=json.dumps(record["response_summary"]) if record.get("response_summary") else None,
            fetched_at=now,
            stale_after=now + timedelta(days=30),
        ))
        created += 1

    db.commit()
    print(f"Enrichments: {created} created, {skipped} already existed")


if __name__ == "__main__":
    seed()
