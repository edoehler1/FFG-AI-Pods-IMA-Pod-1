from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.services.taxonomy import get_capabilities_for_sector
from ingestion.sources.sec_edgar import KNOWN_CIKS

CIK_LOOKUP = KNOWN_CIKS


def generate_financial_analysis(db: Session, company: Company) -> str:
    from ingestion.sources.sec_financials import fetch_company_financials, format_financials_for_prompt

    cik = CIK_LOOKUP.get(company.name)
    financials_text = "No structured financial data available for this company."
    if cik:
        financials = fetch_company_financials(cik, company.name)
        if financials:
            financials_text = format_financials_for_prompt(financials)

    matches = (
        db.query(SignalCompanyMatch)
        .filter(SignalCompanyMatch.company_id == company.id)
        .all()
    )
    matched_ids = [m.signal_id for m in matches]

    filings = (
        db.query(Signal)
        .filter(Signal.id.in_(matched_ids), Signal.source_name == "sec_edgar")
        .order_by(desc(Signal.published_at))
        .limit(10)
        .all()
    ) if matched_ids else []

    company_news = (
        db.query(Signal)
        .filter(Signal.id.in_(matched_ids), Signal.source_name != "sec_edgar")
        .order_by(desc(Signal.published_at))
        .limit(10)
        .all()
    ) if matched_ids else []

    filings_list = "\n".join(
        f"- {s.title} ({s.published_at.strftime('%Y-%m-%d') if s.published_at else 'no date'})"
        for s in filings
    )
    news_list = "\n".join(
        f"- [{s.signal_type}] {s.title}"
        for s in company_news
    )
    capabilities_text = get_capabilities_for_sector(company.industry)

    from app.services.enrichment_reader import get_enrichment_text
    capiq_context = get_enrichment_text(db, "company", company.id, "capiq", max_age_days=90)
    sec_risk_context = get_enrichment_text(db, "company", company.id, "sec_mcp_risk", max_age_days=90)
    sec_mda_context = get_enrichment_text(db, "company", company.id, "sec_mcp_mda", max_age_days=90)
    earnings_context = get_enrichment_text(db, "company", company.id, "earnings", max_age_days=90)
    factiva_context = get_enrichment_text(db, "company", company.id, "factiva", max_age_days=30)

    prompt = f"""You are a senior financial analyst at Strategy& writing a financial intelligence brief.

Company: {company.name}
Industry: {company.industry} / Sub-sector: {company.sub_sector or 'general'}
Client Status: {company.client_status}

## Actual Financial Data (from SEC XBRL filings)
{financials_text}

{f"## Capital IQ Financial Intelligence{chr(10)}{capiq_context}" if capiq_context else ""}

{f"## SEC Filing Analysis — Risk Factors{chr(10)}{sec_risk_context}" if sec_risk_context else ""}

{f"## SEC Filing Analysis — MD&A{chr(10)}{sec_mda_context}" if sec_mda_context else ""}

{f"## Licensed Press Coverage (Factiva){chr(10)}{factiva_context}" if factiva_context else ""}

{f"## Latest Earnings Call Highlights{chr(10)}{earnings_context}" if earnings_context else ""}

## Recent SEC Filings
{filings_list or 'No recent filings.'}

## Recent News About {company.name}
{news_list or 'No recent company-specific news.'}

## S& Capabilities
{capabilities_text}

Analyze this company's financial data and write a brief covering:

1. **Financial Performance** — Analyze the actual numbers. What are the revenue trends? Is revenue growing or declining quarter over quarter? How are margins (operating income vs revenue)? Is SG&A rising or under control? Flag any concerning or notable patterns with the specific numbers.

2. **Key Financial Signals** — Highlight 2-3 specific financial data points that a consulting partner should know about. For example: "SG&A increased from $2.5B to $2.8B QoQ while revenue was flat — suggests cost structure issues" or "R&D spend at $9.4B/year signals heavy investment in next-gen technology."

3. **News Cross-Reference** — Connect the financial picture to recent news. Are the numbers consistent with what's being reported? Does the news explain any financial shifts?

4. **S& Opportunity** — Based on the SPECIFIC financial data, which S& capabilities would address this company's situation? Be concrete: "Cost transformation is indicated by rising SG&A against flat revenue" not "consulting could help."

Use actual dollar figures from the data. Keep it under 500 words. Write for a partner who wants evidence-backed insight, not generic commentary."""

    return _call_llm(prompt)


def _call_llm(prompt: str) -> str:
    from app.services.llm_client import call_llm
    result = call_llm(prompt)
    if not result:
        return "Financial analysis requires a Claude API key. Set ANTHROPIC_API_KEY in .env or ensure PwC Bedrock gateway environment variables are available."
    return result
