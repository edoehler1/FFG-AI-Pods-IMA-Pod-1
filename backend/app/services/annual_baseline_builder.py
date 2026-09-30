"""
Annual Baseline Builder — generates the 12-month intelligence baseline for a company.

Pulls all matched signals, financial analysis, industry benchmarks, and MCP enrichments,
then sends to Claude for structured timeline analysis. The result is the reference document
that weekly reports compare new signals against.
"""

import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.annual_baseline import AnnualBaseline
from app.models.company import Company
from app.models.financial_analysis import FinancialAnalysis, IndustryBenchmark
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.services.enrichment_reader import build_enrichment_context
from app.services.llm_client import call_llm


MAX_SIGNALS_FOR_BASELINE = 60
ENRICHMENT_CAP = 3000


def _gather_historical_signals(db: Session, company_id: str) -> list[dict]:
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)

    matches = (
        db.query(SignalCompanyMatch)
        .filter(
            SignalCompanyMatch.company_id == company_id,
            SignalCompanyMatch.match_type == "name",
        )
        .all()
    )
    if not matches:
        return []

    signal_ids = [m.signal_id for m in matches]
    match_map = {m.signal_id: m for m in matches}

    signals = (
        db.query(Signal)
        .filter(
            Signal.id.in_(signal_ids),
            Signal.source_name != "sec_edgar",
            Signal.published_at >= twelve_months_ago,
        )
        .order_by(desc(Signal.published_at))
        .limit(MAX_SIGNALS_FOR_BASELINE)
        .all()
    )

    events = []
    for s in signals:
        match = match_map.get(s.id)
        date_str = s.published_at.strftime("%Y-%m-%d") if s.published_at else "Unknown"
        tag = match.match_reason if match and match.match_reason not in ("matched", "SEC filing") else ""
        events.append({
            "date": date_str,
            "title": s.title,
            "body": (s.body or "")[:200],
            "tag": tag,
            "score": match.match_score if match else 0,
        })

    return events


def _get_financial_context(db: Session, company: Company) -> str:
    analysis = (
        db.query(FinancialAnalysis)
        .filter(FinancialAnalysis.company_id == company.id)
        .first()
    )
    if not analysis:
        return "No financial analysis available."
    return analysis.content


def _get_benchmark_context(db: Session, company: Company) -> str:
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
        return "No industry benchmark available."

    record = (
        db.query(IndustryBenchmark)
        .filter(IndustryBenchmark.industry == industry_key)
        .first()
    )
    if not record:
        return "No industry benchmark available."

    data = json.loads(record.benchmark_data)
    lines = [f"Sector: {data['industry']} | {data['company_count']} companies | {data.get('fiscal_year', '')}"]

    company_details = data.get("company_details", {}).get(company.name, {})
    rankings = data.get("rankings", {})
    metrics = data.get("metrics", {})

    labels = {
        "operating_margin_pct": ("Operating Margin", "%"),
        "gross_margin_pct": ("Gross Margin", "%"),
        "revenue_growth_yoy_pct": ("Revenue Growth YoY", "%"),
        "rd_as_pct_revenue": ("R&D as % Revenue", "%"),
        "debt_to_equity": ("Debt/Equity", "x"),
        "capex_as_pct_revenue": ("CapEx as % Revenue", "%"),
    }

    for key, (label, unit) in labels.items():
        val = company_details.get(key)
        if val is None:
            continue
        agg = metrics.get(key, {})
        ranking_list = rankings.get(key, [])
        rank_entry = next((r for r in ranking_list if r["company"] == company.name), None)
        rank_str = f"#{rank_entry['rank']}/{len(ranking_list)}" if rank_entry else "unranked"
        median = agg.get("median", "N/A")
        lines.append(f"- {label}: {val}{unit} (rank {rank_str}, median {median}{unit})")

    return "\n".join(lines)


def build_annual_baseline(db: Session, company: Company) -> AnnualBaseline:
    now = datetime.utcnow()
    period_start = (now - timedelta(days=365)).strftime("%Y-%m-%d")
    period_end = now.strftime("%Y-%m-%d")

    events = _gather_historical_signals(db, company.id)
    financial_context = _get_financial_context(db, company)
    benchmark_context = _get_benchmark_context(db, company)

    enrichment_context = build_enrichment_context(db, company.id, company.industry)
    if len(enrichment_context) > ENRICHMENT_CAP:
        enrichment_context = enrichment_context[:ENRICHMENT_CAP] + "\n[...truncated]"

    events_text = "\n".join(
        f"- [{e['date']}] {e['title']}" + (f" [{e['tag']}]" if e.get("tag") else "")
        + (f"\n  {e['body']}" if e.get("body") else "")
        for e in sorted(events, key=lambda x: x["date"])
    ) if events else "No historical signals available."

    prompt = f"""You are a Strategy& intelligence analyst creating an annual baseline timeline for {company.name}.

Your job: analyze 12 months of news and financial data to identify the key strategic events and themes that define this company's current trajectory. This timeline will be the reference baseline for weekly intelligence reports — new signals will be compared against it.

Company: {company.name}
Industry: {company.industry or 'Unknown'} / Sub-sector: {company.sub_sector or 'general'}
Period: {period_start} to {period_end}

## NEWS CORPUS ({len(events)} signals, chronological)
{events_text}

## FINANCIAL ANALYSIS (per-company)
{financial_context}

## INDUSTRY BENCHMARK (vs. sector peers)
{benchmark_context}

{f"## ENRICHED INTELLIGENCE{chr(10)}{enrichment_context}" if enrichment_context else ""}

---

Write the annual baseline in EXACTLY this format:

# {company.name} — Annual Baseline ({period_start} to {period_end})

## Dominant Narrative
2-3 sentences: what is THE story for this company over the past year? What trajectory are they on?

## Key Events Timeline
Chronological list of 15-25 most significant events. For each:
- **[YYYY-MM] Event title.** 1-2 sentence description. Tag: [M&A | Leadership | Regulatory | Financial | Operational | Strategic | Contract | Labor]

## Strategic Themes
3-5 themes that emerge from the timeline. For each:
- **Theme name** — 2-3 sentences explaining the pattern, evidence, and S& implication.

## Financial Trajectory
Company-level financial story PLUS peer comparison. Reference both the per-company analysis and the industry benchmark:
- Revenue, margins, growth relative to sector median and rank
- Whether the company is outperforming or underperforming peers, and why
- Balance sheet trajectory (leveraging/deleveraging)

## Baseline Risks & Opportunities
- Top 3 risks to watch (with evidence from the timeline)
- Top 3 S& opportunities (with specific capability from the taxonomy)

## Comparison Framework
What types of weekly signals would represent:
- ACCELERATION of current trends (bullish for S&)
- CONTRADICTION of current trends (requires reassessment)
- NEW DIRECTION (potential pivot, new opportunity)

Keep the total under 1500 words. Be specific and evidence-based. Optimize for scanability and future comparison."""

    content = call_llm(prompt, max_tokens=4000)
    if not content:
        content = f"Annual baseline generation requires Claude API. {company.name} operates in {company.industry or 'EFS'}."

    key_themes = _extract_key_themes(content)

    existing = (
        db.query(AnnualBaseline)
        .filter(AnnualBaseline.company_id == company.id)
        .first()
    )
    if existing:
        existing.fiscal_year = f"FY{now.year}"
        existing.timeline_content = content
        existing.key_themes = json.dumps(key_themes)
        existing.signal_count = len(events)
        existing.generated_at = now
        db.commit()
        db.refresh(existing)
        return existing

    baseline = AnnualBaseline(
        id=str(uuid.uuid4()),
        company_id=company.id,
        fiscal_year=f"FY{now.year}",
        timeline_content=content,
        key_themes=json.dumps(key_themes),
        signal_count=len(events),
    )
    db.add(baseline)
    db.commit()
    db.refresh(baseline)
    return baseline


def _extract_key_themes(content: str) -> list[dict]:
    themes = []
    in_themes = False
    for line in content.split("\n"):
        if "## Strategic Themes" in line:
            in_themes = True
            continue
        if in_themes and line.startswith("## "):
            break
        if in_themes and line.strip().startswith("- **"):
            match = line.strip().lstrip("- ")
            if "**" in match:
                name = match.split("**")[1] if match.startswith("**") else match.split("**")[0]
                rest = match.split("**")[-1].strip().lstrip("—").lstrip("–").strip()
                themes.append({"theme": name.strip(), "summary": rest[:200]})
    return themes if themes else [{"theme": "Analysis pending", "summary": "Baseline themes not yet extracted"}]


def get_annual_baseline(db: Session, company_id: str) -> AnnualBaseline | None:
    return (
        db.query(AnnualBaseline)
        .filter(AnnualBaseline.company_id == company_id)
        .first()
    )
