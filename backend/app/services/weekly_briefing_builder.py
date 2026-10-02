"""
Weekly Briefing Builder — the final report pipeline.

Pulls all data sources (curated news, industry news, annual baseline, financial
analysis, benchmarks, enrichments, taxonomy, contacts, PwC people, Salesforce)
and sends to Claude for a structured weekly intelligence briefing.

Produces two outputs:
1. Card summary (JSON) for email/portfolio view
2. Full report (markdown) for detail view
"""

import json
import re
import uuid
from datetime import datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.annual_baseline import AnnualBaseline
from app.models.company import Company
from app.models.contact import Contact
from app.models.financial_analysis import FinancialAnalysis
from app.models.weekly_report import WeeklyReport
from app.services.benchmark_builder import get_benchmark
from app.services.company_news_curator import curate_company_news
from app.services.enrichment_reader import build_enrichment_context
from app.services.industry_news_curator import curate_industry_news
from app.services.llm_client import call_llm
from app.services.signal_router import _get_structured_people, _get_structured_pipeline
from app.services.taxonomy import get_capabilities_for_sector


def _current_week_start(now=None):
    if now is None:
        now = datetime.utcnow()
    days_since_sunday = (now.weekday() + 1) % 7
    sunday = now - timedelta(days=days_since_sunday)
    return sunday.strftime("%Y-%m-%d")


def _load_cached_company_news(db: Session, company: Company, days_back: int) -> list[dict]:
    from app.models.curated_news_cache import CuratedNewsCache
    week_start = _current_week_start()
    cached = (
        db.query(CuratedNewsCache)
        .filter(
            CuratedNewsCache.scope == "company",
            CuratedNewsCache.scope_id == company.id,
            CuratedNewsCache.week_start == week_start,
        )
        .first()
    )
    if cached:
        return json.loads(cached.curated_json)
    return curate_company_news(db, company, days_back=days_back)


def _load_cached_industry_news(db: Session, industry: str | None, days_back: int) -> list[dict]:
    if not industry:
        return []
    from app.models.curated_news_cache import CuratedNewsCache
    week_start = _current_week_start()
    cached = (
        db.query(CuratedNewsCache)
        .filter(
            CuratedNewsCache.scope == "industry",
            CuratedNewsCache.scope_id == industry,
            CuratedNewsCache.week_start == week_start,
        )
        .first()
    )
    if cached:
        return json.loads(cached.curated_json)
    return curate_industry_news(db, industry, days_back=days_back)


def build_weekly_briefing(db: Session, company: Company, days_back: int = 7) -> dict:
    now = datetime.utcnow()
    week_start = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
    week_end = now.strftime("%Y-%m-%d")

    company_news = _load_cached_company_news(db, company, days_back)
    industry_news = _load_cached_industry_news(db, company.industry, days_back)
    baseline = db.query(AnnualBaseline).filter(AnnualBaseline.company_id == company.id).first()
    financial = db.query(FinancialAnalysis).filter(FinancialAnalysis.company_id == company.id).first()

    industry_key = _normalize_industry(company.industry)
    benchmark = get_benchmark(db, industry_key) if industry_key else None

    enrichment_ctx = build_enrichment_context(db, company.id, company.industry)
    if len(enrichment_ctx) > 1500:
        enrichment_ctx = enrichment_ctx[:1500] + "\n[...truncated]"

    taxonomy = get_capabilities_for_sector(company.industry)
    people = _get_structured_people(db, company.id)
    pipeline = _get_structured_pipeline(db, company.id)
    contacts = db.query(Contact).filter(Contact.company_id == company.id).order_by(desc(Contact.relationship_strength)).limit(3).all()

    company_news_text = _format_company_news(company_news)
    industry_news_text = _format_industry_news(industry_news[:5])
    baseline_text = _format_baseline(baseline)
    financial_text = _format_financial(financial, benchmark, company.name)
    people_text = _format_people(people)
    pipeline_text = _format_pipeline(pipeline)
    contacts_text = _format_contacts(contacts)

    prompt = f"""You are a Strategy& intelligence director writing a weekly briefing for a partner covering {company.name}.

Company: {company.name}
Industry: {company.industry or 'Unknown'} / Sub-sector: {company.sub_sector or 'general'}
Client Status: {company.client_status}
Period: {week_start} to {week_end}

## S& CAPABILITY TAXONOMY
{taxonomy}

## ANNUAL BASELINE THEMES
{baseline_text}

## THIS WEEK'S CURATED COMPANY SIGNALS (taxonomy-filtered)
{company_news_text}

## INDUSTRY CONTEXT THIS WEEK
{industry_news_text}

## FINANCIAL ANALYSIS & PEER BENCHMARK
{financial_text}

## PwC RELATIONSHIP
{people_text}

## SALESFORCE PIPELINE
{pipeline_text}

## CLIENT CONTACTS
{contacts_text}

{f"## ENRICHED INTELLIGENCE{chr(10)}{enrichment_ctx}" if enrichment_ctx else ""}

---

First, decide: does this week's news create a meaningful consulting opportunity?
- If NO, output ONLY: NO_OPPORTUNITY: [one sentence explaining why nothing is actionable this week]
- If YES, write the full briefing below.

Write the briefing in EXACTLY this format.

FIRST, output a JSON card summary on a single line starting with CARD_JSON:
CARD_JSON: {{"headline": "one sentence — the #1 thing to know this week", "confidence_score": 8, "confidence_tier": "Act Now", "opportunity": "one sentence — the S& opportunity", "taxonomy_tag": "exact capability name", "lead": {{"name": "...", "role": "...", "email": "..."}}, "action": "one sentence — what to do this week"}}

Then write the full report:

# {company.name} — Weekly Briefing ({week_start} to {week_end})

## Baseline Delta
What CHANGED this week vs. the annual baseline?
- Which baseline themes were ACCELERATED by this week's signals?
- Any CONTRADICTIONS to the baseline trajectory?
- Any NEW themes not captured in the baseline?
If nothing changed: "No material change to the baseline trajectory this week."

## This Week's Signals
For each curated company signal:
- **[Taxonomy Tag] Signal title** — why it matters. Suggested action.

## Industry Context
Top 2-3 industry signals that affect this company, with category and relevance.

## Financial Cross-Reference
Connect THIS WEEK'S signals to the financial baseline and benchmark.
Only reference financials when they connect to this week's news. Do NOT restate the financial position.

## The Opportunity
THE specific S& engagement this week's intelligence points to.
- What capability? (exact taxonomy name)
- Why this week? (what new evidence)
- Concrete Phase 1 scope
- Who should pitch it?

## Who Should Act
- GRP: name, email, role
- S& lead / account team: name, email, role
- Client contact: name, title, approach angle
- Salesforce context if any

## Confidence Assessment
Score each dimension 0-2:
- Signal Strength: X/2 — (0=single unconfirmed, 1=top-tier source, 2=multiple corroborating)
- Financial Evidence: X/2 — (0=no connection, 1=directional alignment, 2=specific metric supports it)
- Timing Urgency: X/2 — (0=no forcing function, 1=general window, 2=specific deadline/trigger)
- Taxonomy Fit: X/2 — (0=no capability match, 1=indirect, 2=direct obvious fit)
- Baseline Alignment: X/2 — (0=one-off, 1=loosely related, 2=accelerates/contradicts documented theme)

**Total: X/10** — [Act Now (8-10) | Strong Signal (6-7) | Monitor (3-5) | Noted (0-2)]
One sentence justification.

## Recommended Actions
3-5 bullet points of specific actions for this week, each naming a person.

Keep the full report under 1000 words. Be specific — every claim references evidence."""

    response = call_llm(prompt, max_tokens=4000)
    if not response:
        return _fallback_briefing(company, week_start, week_end, company_news)

    if response.strip().startswith("NO_OPPORTUNITY"):
        no_opp_card = {
            "headline": response.strip(),
            "confidence_score": 0,
            "confidence_tier": "Noted",
            "opportunity": "",
            "taxonomy_tag": "",
            "lead": {},
            "action": "",
        }
        report = _store_briefing(db, company, week_start, week_end, no_opp_card, response.strip(), len(company_news))
        return {
            "card": no_opp_card,
            "full_report": response.strip(),
            "company_id": company.id,
            "company_name": company.name,
            "week_start": week_start,
            "week_end": week_end,
            "signal_count": len(company_news),
            "generated_at": report.generated_at.isoformat() if report.generated_at else now.isoformat(),
            "report_id": report.id,
        }

    card = _parse_card(response)
    full_report = _strip_card_line(response)

    report = _store_briefing(db, company, week_start, week_end, card, full_report, len(company_news))

    return {
        "card": card,
        "full_report": full_report,
        "company_id": company.id,
        "company_name": company.name,
        "week_start": week_start,
        "week_end": week_end,
        "signal_count": len(company_news),
        "generated_at": report.generated_at.isoformat() if report.generated_at else now.isoformat(),
        "report_id": report.id,
    }


def _normalize_industry(industry: str | None) -> str | None:
    if not industry:
        return None
    mapping = {
        "automotive": "automotive",
        "aerospace_defense": "aerospace_defense",
        "energy": "energy",
    }
    return mapping.get(industry.lower(), industry.lower())


def _format_company_news(news: list[dict]) -> str:
    if not news:
        return "No actionable company signals this week."
    lines = []
    for item in news:
        tag = item.get("taxonomy_tag", "")
        title = item["signal"]["title"]
        why = item.get("why_it_matters", "")
        action = item.get("suggested_action", "")
        hl = " [HIGHLIGHTED]" if item.get("highlighted") else ""
        lines.append(f"- [{tag}] {title}{hl}\n  Why: {why}\n  Action: {action}")
    return "\n".join(lines)


def _format_industry_news(news: list[dict]) -> str:
    if not news:
        return "No notable industry signals this week."
    lines = []
    for item in news:
        cat = item.get("category", "")
        title = item["signal"]["title"]
        relevance = item.get("partner_relevance", "")
        lines.append(f"- [{cat.upper()}] {title}\n  {relevance}")
    return "\n".join(lines)


def _format_baseline(baseline: AnnualBaseline | None) -> str:
    if not baseline or not baseline.key_themes:
        return "No annual baseline available."
    try:
        themes = json.loads(baseline.key_themes)
        lines = []
        for t in themes:
            lines.append(f"- **{t['theme']}**: {t['summary']}")
        return "\n".join(lines)
    except (json.JSONDecodeError, KeyError):
        return "Baseline themes unavailable."


def _format_financial(financial: FinancialAnalysis | None, benchmark: dict | None, company_name: str) -> str:
    parts = []
    if financial and financial.content:
        parts.append(financial.content[:1500])
    if benchmark:
        details = benchmark.get("company_details", {}).get(company_name, {})
        metrics = benchmark.get("metrics", {})
        if details:
            lines = [f"\nPeer Benchmark ({benchmark.get('industry', '')} sector, {benchmark.get('company_count', '?')} companies):"]
            for key, label in [("operating_margin_pct", "Op Margin"), ("revenue_growth_yoy_pct", "Rev Growth"), ("debt_to_equity", "D/E")]:
                val = details.get(key)
                med = metrics.get(key, {}).get("median")
                if val is not None and med is not None:
                    unit = "x" if key == "debt_to_equity" else "%"
                    lines.append(f"- {label}: {val}{unit} vs median {med}{unit}")
            parts.append("\n".join(lines))
    return "\n".join(parts) if parts else "No financial data available."


def _format_people(people: dict | None) -> str:
    if not people:
        return "No PwC relationship data."
    lines = []
    if people.get("grp"):
        g = people["grp"]
        lines.append(f"GRP: {g.get('name', '?')} ({g.get('role', 'Partner')}, {g.get('office', '?')})")
    for p in (people.get("account_team") or [])[:3]:
        lines.append(f"Account Team: {p.get('name', '?')} ({p.get('role', '')}, {p.get('office', '')})")
    return "\n".join(lines) if lines else "No PwC relationship data."


def _format_pipeline(pipeline: dict | None) -> str:
    if not pipeline or not pipeline.get("top_opportunity"):
        return "No active Salesforce pipeline."
    opp = pipeline["top_opportunity"]
    val = ""
    if opp.get("value"):
        v = opp["value"]
        val = f" ${v/1_000_000:.1f}M" if v >= 1_000_000 else f" ${v/1_000:.0f}K"
    return f"Active: {opp.get('name', '?')}{val} at {opp.get('stage', '?')} stage. Owner: {opp.get('owner', '?')}."


def _format_contacts(contacts: list) -> str:
    if not contacts:
        return "No client contacts on file."
    lines = []
    for c in contacts:
        email = f" — {c.email}" if c.email else ""
        lines.append(f"- {c.name}, {c.title or 'No title'}{email} (strength: {c.relationship_strength or '?'}/5)")
    return "\n".join(lines)


def _parse_card(response: str) -> dict:
    for line in response.split("\n"):
        if line.strip().startswith("CARD_JSON:"):
            json_str = line.strip()[len("CARD_JSON:"):].strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                break
    return {
        "headline": "Briefing generated — see full report",
        "confidence_score": 0,
        "confidence_tier": "Noted",
        "opportunity": "",
        "taxonomy_tag": "",
        "lead": {},
        "action": "",
    }


def _strip_card_line(response: str) -> str:
    lines = []
    for line in response.split("\n"):
        if line.strip().startswith("CARD_JSON:"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _store_briefing(
    db: Session, company: Company, week_start: str, week_end: str,
    card: dict, full_report: str, signal_count: int,
) -> WeeklyReport:
    existing = (
        db.query(WeeklyReport)
        .filter(
            WeeklyReport.company_id == company.id,
            WeeklyReport.week_start == week_start,
        )
        .first()
    )

    urgency_map = {"Act Now": "high", "Strong Signal": "medium", "Monitor": "low", "Noted": "low"}
    urgency = urgency_map.get(card.get("confidence_tier", ""), "low")

    if existing:
        existing.content = full_report
        existing.signal_count = signal_count
        existing.has_opportunity = card.get("confidence_score", 0) >= 6
        existing.urgency = urgency
        existing.opportunity_summary = json.dumps(card)
        existing.suggested_lead = json.dumps(card.get("lead", {}))
        existing.top_signal_title = card.get("headline", "")
        existing.generated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    report = WeeklyReport(
        id=str(uuid.uuid4()),
        company_id=company.id,
        week_start=week_start,
        week_end=week_end,
        content=full_report,
        signal_count=signal_count,
        has_opportunity=card.get("confidence_score", 0) >= 6,
        urgency=urgency,
        opportunity_summary=json.dumps(card),
        suggested_lead=json.dumps(card.get("lead", {})),
        top_signal_title=card.get("headline", ""),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _fallback_briefing(company: Company, week_start: str, week_end: str, news: list) -> dict:
    return {
        "card": {
            "headline": "Briefing generation requires Claude API.",
            "confidence_score": 0,
            "confidence_tier": "Noted",
            "opportunity": "",
            "taxonomy_tag": "",
            "lead": {},
            "action": "",
        },
        "full_report": f"Weekly briefing for {company.name} requires Claude API.",
        "company_id": company.id,
        "company_name": company.name,
        "week_start": week_start,
        "week_end": week_end,
        "signal_count": len(news),
        "generated_at": datetime.utcnow().isoformat(),
        "report_id": None,
    }
