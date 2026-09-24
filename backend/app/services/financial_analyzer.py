import sys
import os

from sqlalchemy import desc
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.models.company import Company
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.services.taxonomy import get_capabilities_for_sector


CIK_LOOKUP = {
    "Ford Motor Company": "0000037996",
    "General Motors": "0001467858",
    "Tesla Inc": "0001318605",
    "Honda Motor Co": "0000049196",
    "Rivian Automotive": "0001874178",
    "Lucid Group": "0001811210",
    "Stellantis NV": "0000789019",
    "Aptiv": "0001521332",
    "Magna International": "0000749098",
    "Lockheed Martin": "0000936468",
    "Boeing Company": "0000012927",
    "RTX Corporation": "0000101829",
    "Northrop Grumman": "0001133421",
    "General Dynamics": "0000040533",
    "L3Harris Technologies": "0001047122",
    "Leidos Holdings": "0001336920",
    "ExxonMobil": "0000034088",
    "Chevron Corporation": "0000093410",
    "Shell plc": "0001764925",
    "ConocoPhillips": "0001163165",
    "NextEra Energy": "0000753308",
    "Duke Energy": "0000017797",
    "Dominion Energy": "0000715957",
    "Southern Company": "0000092122",
    "AES Corporation": "0000895421",
    "Enbridge Inc": "0000895728",
}


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

    prompt = f"""You are a senior financial analyst at Strategy& writing a financial intelligence brief.

Company: {company.name}
Industry: {company.industry} / Sub-sector: {company.sub_sector or 'general'}
Client Status: {company.client_status}

## Actual Financial Data (from SEC XBRL filings)
{financials_text}

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
    import os
    from app.config import settings

    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    base_url = settings.anthropic_base_url or os.environ.get("ANTHROPIC_BASE_URL")

    if not api_key:
        return "Financial analysis requires a Claude API key. Set ANTHROPIC_API_KEY in .env or ensure PwC Bedrock gateway environment variables are available."

    try:
        import anthropic
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        try:
            import httpx2
            kwargs["http_client"] = httpx2.Client(verify=False)
        except ImportError:
            pass

        model = os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL", "claude-sonnet-4-20250514")
        client = anthropic.Anthropic(**kwargs)
        message = client.messages.create(
            model=model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        return f"Financial analysis generation failed: {e}"
