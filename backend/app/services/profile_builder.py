"""
Company Profile Agent — generates partner-ready annual baseline profiles.

New design:
- At a Glance → The Story → Key Developments → Financial Position → S& Opportunity → Who Should Act
- References financial analysis (not raw XBRL dump)
- 12-month news window (up to 30 signals)
- Maps to real S& taxonomy
- Who Should Act pulls from People Connector structured data
"""

from datetime import datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_profile import CompanyProfile
from app.models.contact import Contact
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.services.enrichment_reader import build_enrichment_context, get_enrichment_text
from app.services.llm_client import call_llm
from app.services.taxonomy import get_capabilities_for_sector


MAX_NEWS_SIGNALS = 30
MCP_CONTEXT_CAP = 4000


def build_company_profile(db: Session, company: Company) -> CompanyProfile:
    financial_narrative = _get_financial_analysis_narrative(db, company)
    benchmark_summary = _get_benchmark_summary(db, company)
    news_summary = _get_company_news(db, company)
    industry_context = _get_industry_context(db, company)
    contacts_summary = _get_contacts(db, company)
    who_should_act = _get_who_should_act(db, company)
    capabilities = get_capabilities_for_sector(company.industry)
    mcp_context = _get_mcp_enrichment_context(db, company)

    prompt = f"""You are a Strategy& intelligence analyst creating an annual baseline company profile for an EFS partner.

Your job: connect financials → news → PwC relationship → opportunity into a clear, actionable profile. This is the document a partner reads before deciding whether to pursue this company.

Company: {company.name}
Industry: {company.industry or 'Unknown'} / Sub-sector: {company.sub_sector or 'general'}
Client Status: {company.client_status}
Geography: {company.geography or 'N/A'}

## FINANCIAL ANALYSIS (from separate analysis document)
{financial_narrative or 'No financial analysis available yet.'}

## INDUSTRY BENCHMARK
{benchmark_summary or 'No benchmark data available.'}

## COMPANY NEWS (past 12 months)
{news_summary or 'No company-specific news found.'}

## INDUSTRY CONTEXT (regulatory, macro, trends)
{industry_context or 'No industry context available.'}

## S& CAPABILITY TAXONOMY
{capabilities}

## PwC CONTACTS & RELATIONSHIPS
{contacts_summary or 'No contacts on file.'}

## PwC RELATIONSHIP INTELLIGENCE (who should act)
{who_should_act or 'No PwC relationship data available.'}

{mcp_context}

---

Write the profile in EXACTLY this format:

# {company.name} — Company Profile

## The Story
THE MOST IMPORTANT PARAGRAPH. This is what the partner reads first. Connect the financial position to the news to the PwC relationship. What is the underlying narrative? What problem or opportunity is emerging? Why should S& care RIGHT NOW?

This must be specific and evidence-based: "Revenue flat at $20B while margins compressed from 8.2% to 6.1% because [news event]. Meanwhile PwC has [relationship context]. The opportunity is [specific thing]."

## Key Developments (Past 12 Months)
8-10 most significant events, chronological. For each:
- Date — What happened — Why it matters for S&
Focus on strategic moves: M&A, restructuring, leadership changes, regulatory actions, major contracts. Not consumer news.

## Financial Position
2-3 sentence narrative summary. Do NOT repeat raw numbers — reference the financial analysis document.
"Revenue flat at $20B while margins compressed due to..." style narrative that tells the financial story.

## S& Opportunity
A SPECIFIC engagement S& could propose, tied directly to The Story above. Not generic consulting.
- What capability from the taxonomy? (tag the exact capability name)
- Why now? (what evidence from news/financials makes this timely?)
- Concrete scope: what would Phase 1 look like?
Taxonomy tag: [exact capability name from the taxonomy list above]
Do NOT include a contacts table or "Key Contacts" sub-section here — contacts belong only in "Who Should Act" below.

## Who Should Act
List each person with their role, email, and why they're the right person:
- GRP: Name — email — relationship owner for this account
- S& Lead: Name — email — led [engagement], knows the operations
- Client contact: Name — department — email — suggested approach

If no PwC relationship data exists, say "No PwC relationship data — this is a new target."

---

Keep the total under 900 words. Be evidence-based — every claim references a specific number, news item, or relationship fact. Write for a busy partner."""

    narrative = call_llm(prompt, max_tokens=2500)
    if not narrative:
        narrative = f"Profile generation requires Claude API. {company.name} operates in the {company.industry or 'EFS'} sector."

    existing = db.query(CompanyProfile).filter(CompanyProfile.company_id == company.id).first()
    if existing:
        existing.financial_summary = financial_narrative
        existing.news_summary = news_summary
        existing.profile_narrative = narrative
        existing.generated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    profile = CompanyProfile(
        company_id=company.id,
        financial_summary=financial_narrative,
        news_summary=news_summary,
        profile_narrative=narrative,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _get_financial_analysis_narrative(db: Session, company: Company) -> str | None:
    from app.models.financial_analysis import FinancialAnalysis
    analysis = (
        db.query(FinancialAnalysis)
        .filter(FinancialAnalysis.company_id == company.id)
        .first()
    )
    if analysis:
        return analysis.content
    return _get_financial_data_fallback(company)


def _get_financial_data_fallback(company: Company) -> str | None:
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


def _get_benchmark_summary(db: Session, company: Company) -> str | None:
    import json
    from app.services.benchmark_builder import get_benchmark

    industry_map = {
        "automotive": "automotive",
        "auto": "automotive",
        "aerospace": "aerospace_defense",
        "aerospace & defense": "aerospace_defense",
        "aerospace_defense": "aerospace_defense",
        "energy": "energy",
        "energy_utilities": "energy",
    }
    industry_key = industry_map.get((company.industry or "").lower())
    if not industry_key:
        return None

    benchmark = get_benchmark(db, industry_key)
    if not benchmark:
        return None

    lines = [f"Sector: {benchmark['industry']} | {benchmark['company_count']} companies | {benchmark['fiscal_year']}"]

    rankings = benchmark.get("rankings", {})
    metrics = benchmark.get("metrics", {})
    company_details = benchmark.get("company_details", {})
    this_company = company_details.get(company.name, {})

    metric_labels = {
        "operating_margin_pct": "Operating Margin",
        "gross_margin_pct": "Gross Margin",
        "revenue_growth_yoy_pct": "Revenue Growth YoY",
        "rd_as_pct_revenue": "R&D as % Revenue",
        "debt_to_equity": "Debt/Equity",
    }

    for key, label in metric_labels.items():
        val = this_company.get(key)
        agg = metrics.get(key, {})
        ranking_list = rankings.get(key, [])
        if val is None:
            continue
        rank_entry = next((r for r in ranking_list if r["company"] == company.name), None)
        rank_str = f"#{rank_entry['rank']}/{len(ranking_list)}" if rank_entry else ""
        median = agg.get("median", "N/A")
        unit = "x" if key == "debt_to_equity" else "%"
        lines.append(f"- {label}: {val}{unit} (rank {rank_str}, median {median}{unit})")

    return "\n".join(lines)


def _get_company_news(db: Session, company: Company) -> str | None:
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)

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
        .filter(
            Signal.id.in_(signal_ids),
            Signal.source_name != "sec_edgar",
            Signal.published_at >= twelve_months_ago,
        )
        .order_by(desc(Signal.published_at))
        .limit(MAX_NEWS_SIGNALS)
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
        email = f" — {c.email}" if c.email else ""
        lines.append(f"- {c.name}, {c.title or 'No title'}{email} — Relationship: {strength}")
    return "\n".join(lines)


def _get_who_should_act(db: Session, company: Company) -> str | None:
    people_eng = get_enrichment_text(db, "company", company.id, "people_engagements", max_age_days=30)
    salesforce = get_enrichment_text(db, "company", company.id, "salesforce", max_age_days=14)

    sections = []
    if people_eng:
        sections.append(f"PwC Engagement History:\n{people_eng}")
    if salesforce:
        sections.append(f"Salesforce Pipeline:\n{salesforce}")
    return "\n\n".join(sections) if sections else None


def _get_mcp_enrichment_context(db: Session, company: Company) -> str:
    context = build_enrichment_context(db, company.id, company.industry)
    if context:
        truncated = context[:MCP_CONTEXT_CAP]
        if len(context) > MCP_CONTEXT_CAP:
            truncated = truncated.rsplit("\n", 1)[0] + "\n[... truncated for token budget]"
        return f"## ENRICHED INTELLIGENCE (from PwC MCP sources)\n\n{truncated}"
    return ""
