import sys
import os
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.models.company import Company
from app.models.company_profile import CompanyProfile
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.services.llm_client import call_llm
from app.services.financial_analyzer import CIK_LOOKUP


def build_company_profile(db: Session, company: Company) -> CompanyProfile:
    financial_summary = _get_financial_summary(company)
    news_summary = _get_news_summary(db, company)

    prompt = f"""Write a brief current-state overview of {company.name} for a Strategy& consulting partner. Max 200 words.

Company: {company.name}
Industry: {company.industry} / {company.sub_sector or 'general'}
Geography: {company.geography or 'N/A'}

## Financial Data
{financial_summary or 'No financial data available (private or non-US company).'}

## Recent News Headlines
{news_summary or 'No recent news found.'}

Cover:
1. What the company does and its market position
2. Financial trajectory (growing/declining/stable, any notable changes)
3. Key recent developments from the news
4. Strategic direction based on the evidence

Be factual and concise. No fluff."""

    narrative = call_llm(prompt, max_tokens=800)
    if not narrative:
        narrative = f"Profile generation requires Claude API. {company.name} operates in the {company.industry or 'EFS'} sector ({company.sub_sector or 'general'})."

    existing = db.query(CompanyProfile).filter(CompanyProfile.company_id == company.id).first()
    if existing:
        existing.financial_summary = financial_summary
        existing.news_summary = news_summary
        existing.profile_narrative = narrative
        existing.generated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    profile = CompanyProfile(
        company_id=company.id,
        financial_summary=financial_summary,
        news_summary=news_summary,
        profile_narrative=narrative,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _get_financial_summary(company: Company) -> str | None:
    cik = CIK_LOOKUP.get(company.name)
    if not cik:
        return None

    try:
        from ingestion.sources.sec_financials import fetch_company_financials, format_financials_for_prompt
        financials = fetch_company_financials(cik, company.name)
        if financials:
            return format_financials_for_prompt(financials)
    except Exception:
        pass
    return None


def _get_news_summary(db: Session, company: Company) -> str | None:
    matches = (
        db.query(SignalCompanyMatch)
        .filter(SignalCompanyMatch.company_id == company.id, SignalCompanyMatch.match_type == "name")
        .all()
    )
    if not matches:
        return None

    signal_ids = [m.signal_id for m in matches]
    news = (
        db.query(Signal)
        .filter(Signal.id.in_(signal_ids), Signal.source_name != "sec_edgar")
        .order_by(desc(Signal.published_at))
        .limit(10)
        .all()
    )

    if not news:
        return None

    lines = []
    for s in news:
        date = s.published_at.strftime("%Y-%m-%d") if s.published_at else ""
        lines.append(f"- [{date}] {s.title}")
    return "\n".join(lines)
