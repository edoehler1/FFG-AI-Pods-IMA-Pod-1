from datetime import datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_analysis import CompanyAnalysis
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch


def get_company_intelligence(db: Session, company: Company) -> dict:
    all_matches = (
        db.query(SignalCompanyMatch)
        .filter(SignalCompanyMatch.company_id == company.id)
        .all()
    )

    name_match_ids = [m.signal_id for m in all_matches if m.match_type == "name"]
    all_matched_ids = [m.signal_id for m in all_matches]

    filings = (
        db.query(Signal)
        .filter(Signal.id.in_(name_match_ids), Signal.source_name == "sec_edgar")
        .order_by(desc(Signal.published_at))
        .all()
    ) if name_match_ids else []

    company_news = (
        db.query(Signal)
        .filter(Signal.id.in_(name_match_ids), Signal.source_name != "sec_edgar")
        .order_by(desc(Signal.published_at))
        .all()
    ) if name_match_ids else []

    six_months_ago = datetime.utcnow() - timedelta(days=180)

    industry_query = (
        db.query(Signal)
        .filter(
            Signal.source_name != "sec_edgar",
            Signal.published_at >= six_months_ago,
        )
    )
    if company.industry:
        industry_query = industry_query.filter(Signal.industry == company.industry)
    if name_match_ids:
        industry_query = industry_query.filter(~Signal.id.in_(name_match_ids))

    raw_industry = industry_query.order_by(desc(Signal.published_at)).limit(50).all()
    seen_titles = set()
    deduped = []
    for s in raw_industry:
        if s.title in seen_titles:
            continue
        seen_titles.add(s.title)
        deduped.append(s)
        if len(deduped) >= 30:
            break

    industry_results = _filter_industry_news_with_claude(deduped, company)

    return {
        "filings": filings,
        "company_news": company_news,
        "industry_news": [r["signal"] for r in industry_results],
        "industry_news_categories": {r["signal"].id: r["category"] for r in industry_results},
    }


def _filter_industry_news_with_claude(signals: list, company) -> list[dict]:
    """Returns list of {"signal": Signal, "category": str}"""
    if not signals:
        return []

    from app.services.llm_client import call_llm, is_llm_available
    import json, re as _re

    default = [{"signal": s, "category": "general"} for s in signals[:15]]

    if not is_llm_available():
        return default

    articles_text = []
    for i, s in enumerate(signals):
        articles_text.append(f"{i}. [{s.signal_type}] {s.title}")

    prompt = f"""You are filtering industry news for a Strategy& partner covering {company.name} ({company.industry}/{company.sub_sector or 'general'}).

Keep only articles that provide valuable context for consulting. For each kept article, categorize it.

Categories:
- "regulatory" — regulation, policy, government action, compliance
- "macro" — tariffs, trade, economic trends, supply chain, labor, interest rates
- "company_moves" — specific company actions: earnings, M&A, restructuring, leadership changes, partnerships
- "trends" — technology shifts, industry outlook, emerging themes, innovation

Remove: generic unrelated regulations, consumer content, local news, entertainment.

Articles:
{chr(10).join(articles_text)}

Return ONLY valid JSON array of objects. Example: [{{"index": 0, "category": "regulatory"}}, {{"index": 3, "category": "macro"}}]
Keep the 10-15 most valuable articles."""

    response = call_llm(prompt, max_tokens=1000)
    if not response:
        return default

    try:
        cleaned = _re.sub(r"```\w*\s*", "", response).strip()
        json_match = _re.search(r'\[.*\]', cleaned, _re.DOTALL)
        if not json_match:
            return default
        results = json.loads(json_match.group())
        output = []
        for r in results:
            idx = r.get("index", -1)
            cat = r.get("category", "general")
            if isinstance(idx, int) and 0 <= idx < len(signals):
                output.append({"signal": signals[idx], "category": cat})
        return output if output else default
    except Exception as e:
        print(f"Industry news filter parse error: {e}")
        return default


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
    from app.services.llm_client import call_llm
    result = call_llm(prompt)
    return result if result else _template_fallback(prompt)


def _template_fallback(prompt: str) -> str:
    return (
        "## AI Analysis Unavailable\n\n"
        "Claude API is not configured. Set ANTHROPIC_API_KEY in your .env file "
        "or ensure the PwC Bedrock gateway environment variables are available.\n\n"
        "Once configured, this section will contain an AI-generated intelligence brief "
        "covering financial overview, market context, S& opportunity assessment, "
        "and recommended actions for this company."
    )
