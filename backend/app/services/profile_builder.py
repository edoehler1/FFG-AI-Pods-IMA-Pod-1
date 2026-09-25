"""
Company Profile Agent — generates comprehensive "current state" profiles.

Connects financials to news to find the underlying story and S& opportunity.
Runs once per company, saved permanently. Refreshes on new quarterly filings.
"""

import sys
import os
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.models.company import Company
from app.models.company_profile import CompanyProfile
from app.models.contact import Contact
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.services.llm_client import call_llm
from app.services.taxonomy import get_capabilities_for_sector


def build_company_profile(db: Session, company: Company) -> CompanyProfile:
    financial_summary = _get_financial_data(company)
    news_summary = _get_company_news(db, company)
    industry_context = _get_industry_context(db, company)
    contacts_summary = _get_contacts(db, company)
    capabilities = get_capabilities_for_sector(company.industry)
    mcp_context = _get_mcp_enrichment_context(db, company)

    prompt = f"""You are a Strategy& intelligence analyst creating a comprehensive company profile for an EFS partner.

Your job is to find THE STORY — connect the financial numbers to the news to identify the underlying cause or problem that represents a consulting opportunity.

Company: {company.name}
Industry: {company.industry} / Sub-sector: {company.sub_sector or 'general'}
Client Status: {company.client_status}
Geography: {company.geography or 'N/A'}

## FINANCIAL DATA (from SEC XBRL — actual numbers)
{financial_summary or 'No financial data available (private or non-US filer).'}

## COMPANY NEWS (past year, relevance-filtered)
{news_summary or 'No company-specific news found.'}

## INDUSTRY CONTEXT (regulatory, macro, trends)
{industry_context or 'No industry context available.'}

## S& CAPABILITIES (placeholder taxonomy — will be refined)
{capabilities}

## CONTACTS IN SYSTEM
{contacts_summary or 'No contacts on file.'}

{mcp_context}

---

Write the profile in EXACTLY this format:

# {company.name} — Current State Profile

## Company Overview
What they do, market position, competitive standing. 2-3 sentences.

## Financial Picture
Analyze the actual numbers. Revenue trajectory across quarters. Margin trends (operating income / revenue). SG&A changes. Debt position. Flag anything notable — growing, declining, volatile, stable. Use specific dollar figures.

## Recent Developments
Summarize the 5-7 most important news items from the past year. One line each. Focus on strategic moves, not consumer news.

## The Story
THIS IS THE MOST IMPORTANT SECTION. Connect the financial data to the news. What is the underlying narrative?

Example: "SG&A rose from $2.5B to $2.8B over 3 quarters while revenue stayed flat at ~$43B. News shows the company is investing heavily in EV transition (new plant, R&D hiring) while legacy operations haven't been restructured. The gap between investment and returns is widening — they're spending to transform but haven't cut the old cost structure."

Find the real story. What do the numbers tell us that the headlines don't? What problem is building?

## S& Opportunity
Based on The Story above, what SPECIFIC engagement could S& propose? Not generic "strategy consulting" — a concrete project tied to the evidence.

Example: "Operating model transformation — restructure legacy auto manufacturing operations to fund EV scale-up without further margin erosion. Phase 1: cost diagnostic ($X SG&A vs peers). Phase 2: org redesign for dual powertrain operations."

## Key Contacts
List contacts with relationship strength and suggested approach.

---

Keep the total under 800 words. Be evidence-based — every claim should reference a specific number or news item. Write for a busy partner who needs to decide whether to pursue this company."""

    narrative = call_llm(prompt, max_tokens=2500)
    if not narrative:
        narrative = f"Profile generation requires Claude API. {company.name} operates in the {company.industry or 'EFS'} sector."

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


def _get_financial_data(company: Company) -> str | None:
    from app.services.financial_analyzer import CIK_LOOKUP
    cik = CIK_LOOKUP.get(company.name)
    if not cik:
        from app.services.onboarding import _lookup_cik
        cik = _lookup_cik(company.name)
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


def _get_company_news(db: Session, company: Company) -> str | None:
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
        .limit(15)
        .all()
    )
    if not news:
        return None

    lines = []
    for s in news:
        date = s.published_at.strftime("%Y-%m-%d") if s.published_at else ""
        reason = ""
        match = next((m for m in matches if m.signal_id == s.id), None)
        if match and match.match_reason:
            reason = f" | Relevance: {match.match_reason}"
        lines.append(f"- [{date}] {s.title}{reason}")
    return "\n".join(lines)


def _get_industry_context(db: Session, company: Company) -> str | None:
    from datetime import timedelta
    six_months_ago = datetime.utcnow() - timedelta(days=180)

    query = (
        db.query(Signal)
        .filter(
            Signal.source_name != "sec_edgar",
            Signal.published_at >= six_months_ago,
            Signal.news_category.in_(["regulatory", "macro", "trends"]),
        )
    )
    if company.industry:
        query = query.filter(Signal.industry == company.industry)

    signals = query.order_by(desc(Signal.published_at)).limit(10).all()
    if not signals:
        return None

    lines = []
    for s in signals:
        cat = f"[{s.news_category}]" if s.news_category else ""
        lines.append(f"- {cat} {s.title}")
    return "\n".join(lines)


def _get_contacts(db: Session, company: Company) -> str | None:
    contacts = db.query(Contact).filter(Contact.company_id == company.id).all()
    if not contacts:
        return None

    lines = []
    strength_labels = {1: "Very Weak", 2: "Weak", 3: "Moderate", 4: "Strong", 5: "Very Strong"}
    for c in contacts:
        strength = strength_labels.get(c.relationship_strength, "Unknown")
        lines.append(f"- {c.name}, {c.title or 'No title'} — Relationship: {strength}")
    return "\n".join(lines)


def _get_mcp_enrichment_context(db: Session, company: Company) -> str:
    from app.services.enrichment_reader import build_enrichment_context
    context = build_enrichment_context(db, company.id, company.industry)
    if context:
        return f"## ENRICHED INTELLIGENCE (from PwC MCP sources)\n\n{context}"
    return ""
