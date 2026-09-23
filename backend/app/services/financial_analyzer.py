from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.services.taxonomy import get_capabilities_for_sector


def generate_financial_analysis(db: Session, company: Company) -> str:
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
        .all()
    ) if matched_ids else []

    company_news = (
        db.query(Signal)
        .filter(Signal.id.in_(matched_ids), Signal.source_name != "sec_edgar")
        .order_by(desc(Signal.published_at))
        .limit(10)
        .all()
    ) if matched_ids else []

    if not filings:
        return "No SEC filings found for this company. Financial analysis requires filing data."

    filings_detail = []
    for f in filings[:15]:
        form = "Unknown"
        if " — " in f.title:
            form = f.title.split(" — ")[1].replace(" filing", "")
        date_str = f.published_at.strftime("%Y-%m-%d") if f.published_at else "no date"
        filings_detail.append(f"- **{form}** ({date_str}): {f.body or 'No description'}")

    news_context = "\n".join(
        f"- [{s.signal_type}] {s.title}"
        for s in company_news[:8]
    )

    capabilities_text = get_capabilities_for_sector(company.industry)

    prompt = f"""You are a senior financial analyst at Strategy& writing a financial intelligence brief.

Company: {company.name}
Industry: {company.industry} / Sub-sector: {company.sub_sector or 'general'}
Client Status: {company.client_status}

## SEC Filing History (most recent first)
{chr(10).join(filings_detail)}

## Recent News About {company.name}
{news_context or 'No recent company-specific news.'}

## S& Capabilities
{capabilities_text}

Analyze this company's financial trajectory and write a brief covering:

1. **Filing Activity Pattern** — What does the filing cadence tell us? Any unusual 8-K activity? When were the last 10-K and 10-Q filed?
2. **Financial Trajectory** — Based on the filing types and timing, what can we infer about the company's financial health and strategic direction? Flag anything that suggests major changes (restructuring, M&A activity, executive changes via 8-K, etc.)
3. **News Cross-Reference** — How do recent news signals connect to or explain the filing activity? Build an evidence-backed narrative connecting the financial signals to market events.
4. **Consulting Opportunity** — Based on the financial picture AND the news context, which SPECIFIC S& capabilities from the list would be most valuable to this company right now? Explain why with evidence from the filings and news.

Be specific about numbers when available (e.g., "3 8-K filings in Q3 suggests elevated M&A or restructuring activity"). Keep it under 500 words. Write for a partner who wants to know: should I pitch this company, and what should I pitch?"""

    return _call_llm(prompt)


def _call_llm(prompt: str) -> str:
    import os
    from app.config import settings

    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL")

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
