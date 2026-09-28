"""
Weekly Report Agent — generates personalized insights per company.

Cross-references the week's news against saved company profiles to find
actionable consulting opportunities. Only generates a report if there's
something worth reporting.
"""

import json
import re
from datetime import datetime, timedelta

from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_profile import CompanyProfile
from app.models.contact import Contact
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.models.weekly_report import WeeklyReport
from app.services.llm_client import call_llm
from app.services.taxonomy import get_capabilities_for_sector


def _ensure_columns(db: Session):
    new_cols = [
        ("urgency", "VARCHAR(10)"),
        ("opportunity_summary", "TEXT"),
        ("suggested_lead", "TEXT"),
        ("financial_cross_ref", "TEXT"),
        ("top_signal_title", "TEXT"),
    ]
    for col_name, col_type in new_cols:
        try:
            db.execute(text(f"ALTER TABLE weekly_reports ADD COLUMN {col_name} {col_type}"))
            db.commit()
        except Exception:
            db.rollback()


def _parse_report_fields(response: str) -> dict:
    fields: dict = {
        "urgency": None,
        "opportunity_summary": None,
        "suggested_lead": None,
        "financial_cross_ref": None,
        "top_signal_title": None,
    }

    urgency_match = re.search(r"URGENCY:\s*(high|medium|low)", response, re.IGNORECASE)
    if urgency_match:
        fields["urgency"] = urgency_match.group(1).lower()

    lead_match = re.search(r"LEAD:\s*(.+?)(?:\n|$)", response)
    if lead_match:
        raw_lead = lead_match.group(1).strip()
        name_role = re.match(r"(.+?)\s*\((.+?)\)", raw_lead)
        if name_role:
            parts = name_role.group(2).split(",", 1)
            role = parts[0].strip()
            office = parts[1].strip() if len(parts) > 1 else None
            lead_obj = {"name": name_role.group(1).strip(), "role": role}
            if office:
                lead_obj["office"] = office
            fields["suggested_lead"] = json.dumps(lead_obj)
        else:
            fields["suggested_lead"] = json.dumps({"name": raw_lead})

    sections = re.split(r"^## ", response, flags=re.MULTILINE)
    for section in sections:
        lines = section.strip()
        if lines.startswith("What Happened This Week"):
            body = lines.split("\n", 1)[1].strip() if "\n" in lines else ""
            first_sentence = re.split(r"(?<=[.!?])\s", body, maxsplit=1)
            fields["top_signal_title"] = first_sentence[0][:500] if first_sentence else None
        elif lines.startswith("The Opportunity"):
            body = lines.split("\n", 1)[1].strip() if "\n" in lines else ""
            sentences = re.split(r"(?<=[.!?])\s", body, maxsplit=2)
            fields["opportunity_summary"] = " ".join(sentences[:2])[:1000] if sentences else None
        elif lines.startswith("Why It Matters"):
            body = lines.split("\n", 1)[1].strip() if "\n" in lines else ""
            fields["financial_cross_ref"] = body[:2000] if body else None

    return fields


def generate_weekly_reports(
    db: Session,
    days_back: int = 7,
    company_ids: list[str] | None = None,
) -> list[dict]:
    """Generate weekly reports for all companies (or specific ones)."""
    _ensure_columns(db)
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
            Signal.news_category.in_(["regulatory", "macro", "trends", "company_moves"]) | Signal.news_category.is_(None),
        )
        .order_by(desc(Signal.published_at))
        .limit(5)
        .all()
    )

    if not week_news and not industry_signals:
        return None

    profile = db.query(CompanyProfile).filter(CompanyProfile.company_id == company.id).first()
    profile_context = profile.profile_narrative[:2500] if profile else "No company profile available."
    financial_baseline = profile.financial_summary if profile else None

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

    from app.services.enrichment_reader import build_enrichment_context
    enrichment_context = build_enrichment_context(db, company.id, company.industry)
    if len(enrichment_context) > 6000:
        enrichment_context = enrichment_context[:6000] + "\n[...truncated]"

    prompt = f"""You are a Strategy& intelligence agent generating a weekly insight report for a partner.

Your job: determine if this week's news creates or advances a consulting opportunity for {company.name}. If yes, explain it clearly. If not, say so briefly.

## Company Profile (saved baseline)
{profile_context}

{f"## Financial Baseline (SEC XBRL){chr(10)}{financial_baseline}" if financial_baseline else ""}

## This Week's Company News ({week_start} to {week_end})
{news_text}

## Industry Context This Week
{industry_text}

{f"## Enriched Intelligence (all available MCP sources){chr(10)}{enrichment_context}" if enrichment_context else ""}

## Contacts
{contacts_text}

## S& Capabilities
{capabilities}

---

First, decide: does this week's news create a meaningful consulting opportunity?
- If YES, write the full report below.
- If NO, write: "NO_OPPORTUNITY: [one sentence explaining why nothing is actionable this week]"

If YES, write in EXACTLY this format:

## What Happened This Week
1-2 sentence summary of the key signal(s).

## Why It Matters
Compare this week's news to the financial baseline above. Does it accelerate a known trend, contradict it, or create a new financial implication? Cite specific numbers from the baseline. If no financial data exists, analyze the strategic implications instead.

## PwC Context
If PwC engagement data, People Connector data, or Salesforce pipeline data is present in the enriched intelligence above, summarize it here: name the Global Relationship Partner (GRP) and account team members by name and office. If Salesforce pipeline data exists, note the deal stage and value. If no PwC data exists, write "No PwC engagement data available."

## The Opportunity
What specific problem does this create or worsen that S& could solve? Concrete engagement tied to evidence from BOTH the news and the financials. Not generic.

## Who Should Act
Name the specific PwC person who should lead outreach. Priority order: GRP > account team > recent engagement staff > manual contacts from the contacts list above. Include their name and role. If no PwC people data exists, recommend from the manual contacts list.

## Recommended Action
What to say, when to reach out, and urgency level (high/medium/low). Tailor the framing to the relationship status and the specific signal.

URGENCY: [high/medium/low]
LEAD: [Name (Role, Office)]

Keep it under 500 words. Every claim tied to evidence."""

    response = call_llm(prompt, max_tokens=2000)
    if not response:
        return None

    has_opportunity = not response.strip().startswith("NO_OPPORTUNITY")
    parsed = _parse_report_fields(response) if has_opportunity else {}

    report = WeeklyReport(
        company_id=company.id,
        week_start=week_start,
        week_end=week_end,
        content=response,
        signal_count=len(week_news) + len(industry_signals),
        has_opportunity=has_opportunity,
        urgency=parsed.get("urgency"),
        opportunity_summary=parsed.get("opportunity_summary"),
        suggested_lead=parsed.get("suggested_lead"),
        financial_cross_ref=parsed.get("financial_cross_ref"),
        top_signal_title=parsed.get("top_signal_title"),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
