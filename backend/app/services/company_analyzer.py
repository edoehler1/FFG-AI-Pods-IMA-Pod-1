from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_analysis import CompanyAnalysis
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch


def get_company_intelligence(db: Session, company: Company) -> dict:
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
        .all()
    ) if matched_ids else []

    industry_query = db.query(Signal).filter(Signal.source_name != "sec_edgar")
    if company.industry:
        industry_query = industry_query.filter(Signal.industry == company.industry)
    if company.sub_sector:
        industry_query = industry_query.filter(Signal.sub_sector == company.sub_sector)
    if matched_ids:
        industry_query = industry_query.filter(~Signal.id.in_(matched_ids))
    industry_news = industry_query.order_by(desc(Signal.published_at)).limit(20).all()

    return {
        "filings": filings,
        "company_news": company_news,
        "industry_news": industry_news,
    }


def generate_company_analysis(db: Session, company: Company) -> CompanyAnalysis:
    from app.services.taxonomy import get_capabilities_for_sector

    intel = get_company_intelligence(db, company)

    filings_text = "\n".join(
        f"- {s.title} ({s.published_at.strftime('%Y-%m-%d') if s.published_at else 'no date'})"
        for s in intel["filings"][:10]
    )
    company_news_text = "\n".join(
        f"- [{s.signal_type}] {s.title}"
        for s in intel["company_news"][:10]
    )
    industry_news_text = "\n".join(
        f"- [{s.signal_type}, {s.sub_sector or 'general'}] {s.title}"
        for s in intel["industry_news"][:10]
    )

    capabilities_text = get_capabilities_for_sector(company.industry)

    prompt = f"""You are a Strategy& intelligence analyst preparing a company brief for an EFS partner.

Company: {company.name}
Industry: {company.industry} / Sub-sector: {company.sub_sector or 'general'}
Client Status: {company.client_status}
Geography: {company.geography or 'N/A'}

## Recent SEC Filings
{filings_text or 'No filings found.'}

## Company-Specific News
{company_news_text or 'No company-specific news found.'}

## Industry & Macro Context ({company.industry}, {company.sub_sector or 'general'})
{industry_news_text or 'No industry news found.'}

## S& Capabilities Available for This Sector
{capabilities_text}

Based on the above, write a concise intelligence brief covering:

1. **Financial Overview** — What do the recent filings tell us about this company's trajectory? Any notable changes?
2. **News & Market Context** — What's happening around this company and in their industry that matters?
3. **S& Opportunity Assessment** — Based on the signals, recommend SPECIFIC S& capabilities from the list above. Don't be generic — name the exact capability and explain why this company needs it now based on the evidence.
4. **Recommended Action** — What should the partner do next? (Reach out, monitor, prepare a pitch deck, etc.)

Keep it under 400 words. Be direct and specific — this is for a busy partner."""

    narrative = _call_llm(prompt)

    existing = db.query(CompanyAnalysis).filter(CompanyAnalysis.company_id == company.id).first()
    if existing:
        existing.narrative = narrative
        existing.signal_count = len(intel["company_news"]) + len(intel["industry_news"])
        existing.filing_count = len(intel["filings"])
        existing.generated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    analysis = CompanyAnalysis(
        company_id=company.id,
        narrative=narrative,
        signal_count=len(intel["company_news"]) + len(intel["industry_news"]),
        filing_count=len(intel["filings"]),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def _call_llm(prompt: str) -> str:
    import os
    from app.config import settings

    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    base_url = settings.anthropic_base_url or os.environ.get("ANTHROPIC_BASE_URL")

    if not api_key:
        return _template_fallback(prompt)

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
        print(f"Claude API error in company analyzer: {e}")
        return _template_fallback(prompt)


def _template_fallback(prompt: str) -> str:
    return (
        "## AI Analysis Unavailable\n\n"
        "Claude API is not configured. Set ANTHROPIC_API_KEY in your .env file "
        "or ensure the PwC Bedrock gateway environment variables are available.\n\n"
        "Once configured, this section will contain an AI-generated intelligence brief "
        "covering financial overview, market context, S& opportunity assessment, "
        "and recommended actions for this company."
    )
