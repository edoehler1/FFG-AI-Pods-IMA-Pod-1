"""
Weekly Report Agent — generates personalized insights per company.

Cross-references the week's news against saved company profiles to find
actionable consulting opportunities. Only generates a report if there's
something worth reporting.
"""

from datetime import datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_profile import CompanyProfile
from app.models.contact import Contact
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.models.weekly_report import WeeklyReport
from app.services.llm_client import call_llm
from app.services.taxonomy import get_capabilities_for_sector


def generate_weekly_reports(
    db: Session,
    days_back: int = 7,
    company_ids: list[str] | None = None,
) -> list[dict]:
    """Generate weekly reports for all companies (or specific ones)."""
    now = datetime.utcnow()
    week_start = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
    week_end = now.strftime("%Y-%m-%d")

    if company_ids:
        companies = db.query(Company).filter(Company.id.in_(company_ids)).all()
    else:
        companies = db.query(Company).all()

    results = []
    for company in companies:
        existing = (
            db.query(WeeklyReport)
            .filter(
                WeeklyReport.company_id == company.id,
                WeeklyReport.week_start == week_start,
            )
            .first()
        )
        if existing:
            results.append({"company": company.name, "status": "already_generated", "has_opportunity": existing.has_opportunity})
            continue

        report = _generate_for_company(db, company, week_start, week_end, days_back)
        if report:
            results.append({"company": company.name, "status": "generated", "has_opportunity": report.has_opportunity})
        else:
            results.append({"company": company.name, "status": "no_relevant_news"})

    return results


def _generate_for_company(
    db: Session, company: Company, week_start: str, week_end: str, days_back: int,
) -> WeeklyReport | None:
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    matches = (
        db.query(SignalCompanyMatch)
        .filter(SignalCompanyMatch.company_id == company.id, SignalCompanyMatch.match_type == "name")
        .all()
    )
    signal_ids = [m.signal_id for m in matches]

    week_news = (
        db.query(Signal)
        .filter(
            Signal.id.in_(signal_ids),
            Signal.source_name != "sec_edgar",
            Signal.published_at >= cutoff,
        )
        .order_by(desc(Signal.published_at))
        .limit(10)
        .all()
    ) if signal_ids else []

    industry_signals = (
        db.query(Signal)
        .filter(
            Signal.source_name != "sec_edgar",
            Signal.published_at >= cutoff,
            Signal.industry == company.industry,
            Signal.news_category.in_(["regulatory", "macro", "trends"]),
        )
        .order_by(desc(Signal.published_at))
        .limit(5)
        .all()
    )

    if not week_news and not industry_signals:
        return None

    profile = db.query(CompanyProfile).filter(CompanyProfile.company_id == company.id).first()
    profile_context = profile.profile_narrative[:1500] if profile else "No company profile available."

    contacts = db.query(Contact).filter(Contact.company_id == company.id).all()
    contacts_text = "\n".join(
        f"- {c.name}, {c.title or 'No title'} (strength: {c.relationship_strength or '?'}/5)"
        for c in contacts
    ) if contacts else "No contacts on file."

    news_text = "\n".join(
        f"- [{s.published_at.strftime('%m/%d') if s.published_at else '?'}] {s.title}"
        for s in week_news
    ) if week_news else "No company-specific news this week."

    industry_text = "\n".join(
        f"- [{s.news_category}] {s.title}"
        for s in industry_signals
    ) if industry_signals else "No notable industry signals this week."

    capabilities = get_capabilities_for_sector(company.industry)

    prompt = f"""You are a Strategy& intelligence agent generating a weekly insight report for a partner.

Your job: determine if this week's news creates or advances a consulting opportunity for {company.name}. If yes, explain it clearly. If not, say so briefly.

## Company Profile (saved baseline)
{profile_context}

## This Week's Company News ({week_start} to {week_end})
{news_text}

## Industry Context This Week
{industry_text}

## Contacts
{contacts_text}

## S& Capabilities (placeholder taxonomy)
{capabilities}

---

First, decide: does this week's news create a meaningful consulting opportunity?
- If YES, write the full report below.
- If NO, write: "NO_OPPORTUNITY: [one sentence explaining why nothing is actionable this week]"

If YES, write in this format:

## What Happened This Week
1-2 sentence summary of the key signal(s).

## Why It Matters
Connect this week's news to the company's financial picture and story from the profile. Does this accelerate a known problem? Create a new one? Validate an existing trend?

## The Opportunity
What specific problem does this create or worsen that S& could solve? Concrete engagement tied to evidence from BOTH the news and the financials. Not generic.

## Recommended Action
Who to contact (from the contacts list), what to say, and urgency level (high/medium/low).

Keep it under 300 words. Every claim tied to evidence."""

    response = call_llm(prompt, max_tokens=1500)
    if not response:
        return None

    has_opportunity = not response.strip().startswith("NO_OPPORTUNITY")

    report = WeeklyReport(
        company_id=company.id,
        week_start=week_start,
        week_end=week_end,
        content=response,
        signal_count=len(week_news) + len(industry_signals),
        has_opportunity=has_opportunity,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
