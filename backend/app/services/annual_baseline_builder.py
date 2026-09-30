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


def _get_historical_enrichments(db: Session, company_id: str) -> list[dict]:
    import re
    from app.models.mcp_enrichment import MCPEnrichment
    historical_sources = ["earnings_historical", "capiq_historical", "factiva_historical"]
    events = []
    for source in historical_sources:
        record = (
            db.query(MCPEnrichment)
            .filter(
                MCPEnrichment.entity_type == "company",
                MCPEnrichment.entity_id == company_id,
                MCPEnrichment.mcp_source == source,
            )
            .first()
        )
        if not record or not record.response_markdown:
            continue

        for block in record.response_markdown.split("\n## "):
            block = block.strip()
            if not block:
                continue
            date_match = re.search(r"\((\w+ \d+, \d{4})\)", block)
            if date_match:
                from datetime import datetime as dt
                try:
                    parsed = dt.strptime(date_match.group(1), "%b %d, %Y")
                    date_str = parsed.strftime("%Y-%m-%d")
                except ValueError:
                    date_str = "Unknown"
            else:
                date_match2 = re.search(r"(\d{4}-\d{2})", block)
                date_str = date_match2.group(1) + "-01" if date_match2 else "Unknown"

            first_line = block.split("\n")[0].strip().lstrip("# ")
            body = "\n".join(block.split("\n")[1:]).strip()[:300]
            events.append({
                "date": date_str,
                "title": first_line,
                "body": body,
                "tag": "Earnings" if "earnings" in source.lower() else "KeyDevelopment",
                "score": 0.9,
            })

    return events


def build_annual_baseline(db: Session, company: Company) -> AnnualBaseline:
    now = datetime.utcnow()
    period_start = (now - timedelta(days=365)).strftime("%Y-%m-%d")
    period_end = now.strftime("%Y-%m-%d")

    enrichment_events = _get_historical_enrichments(db, company.id)
    signal_events = _gather_historical_signals(db, company.id)
    events = enrichment_events + signal_events
    financial_context = _get_financial_context(db, company)
    benchmark_context = _get_benchmark_context(db, company)

    enrichment_context = build_enrichment_context(db, company.id, company.industry)
    enrichment_lines = []
    skip_section = False
    for line in enrichment_context.split("\n"):
        if "Engagement History" in line or "PwC Engagement" in line:
            skip_section = True
            continue
        if skip_section and line.startswith("## "):
            skip_section = False
        if not skip_section:
            enrichment_lines.append(line)
    enrichment_context = "\n".join(enrichment_lines)
    if len(enrichment_context) > ENRICHMENT_CAP:
        enrichment_context = enrichment_context[:ENRICHMENT_CAP] + "\n[...truncated]"

    earnings_events = [e for e in events if e.get("tag") == "Earnings"]
    other_events = [e for e in events if e.get("tag") != "Earnings"]

    earnings_text = "\n".join(
        f"- [{e['date']}] {e['title']}\n  {e['body']}"
        for e in sorted(earnings_events, key=lambda x: x["date"])
    ) if earnings_events else "No quarterly earnings data available."

    news_text = "\n".join(
        f"- [{e['date']}] {e['title']}" + (f" [{e['tag']}]" if e.get("tag") else "")
        + (f"\n  {e['body']}" if e.get("body") else "")
        for e in sorted(other_events, key=lambda x: x["date"])
    ) if other_events else "No news signals available."

    prompt = f"""You are a Strategy& intelligence analyst creating an annual baseline timeline for {company.name}.

Your job: analyze 12 months of news, earnings, and financial data to identify the key strategic events and themes that define this company's current trajectory. This timeline will be the reference baseline for weekly intelligence reports — new signals will be compared against it.

CRITICAL INSTRUCTIONS:
1. The Key Events Timeline MUST span the full 12-month period. Events from Oct-Dec 2025, Jan-Mar 2026, Apr-Jun 2026, AND Jul-Sep 2026 must ALL be represented.
2. Every earnings quarter in the HISTORICAL EARNINGS section below MUST appear as a separate timeline entry with its actual date (e.g. [2025-07], [2025-10], [2026-01], [2026-04]).
3. Key developments from CapIQ (M&A, divestitures, regulatory actions) MUST appear with their actual dates.
4. Recent news signals supplement the earnings and key developments — they do NOT replace them.
5. If a quarter has no events from any source, note the gap explicitly.

Company: {company.name}
Industry: {company.industry or 'Unknown'} / Sub-sector: {company.sub_sector or 'general'}
Period: {period_start} to {period_end}

## QUARTERLY EARNINGS (MUST appear in timeline — each one is a major event)
{earnings_text}

## NEWS & KEY DEVELOPMENTS ({len(other_events)} signals)
{news_text}

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
Chronological list, oldest first, of the most significant events. For each:
- **[YYYY-MM-DD] Event title.** 1-2 sentence description. Tag: [Earnings | M&A | Leadership | Regulatory | Financial | Operational | Strategic | Contract | Labor]

START with these earnings events (copy them in, then add news events around them):
{earnings_text}

Then interleave the news and key development events from the corpus above in chronological order.

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

    if earnings_events:
        content = _inject_earnings_into_timeline(content, earnings_events)

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


def _inject_earnings_into_timeline(content: str, earnings_events: list[dict]) -> str:
    lines = content.split("\n")
    result = []
    injected = False

    for line in lines:
        result.append(line)
        if not injected and "Key Events" in line and line.strip().startswith("##"):
            earnings_lines = []
            for e in sorted(earnings_events, key=lambda x: x["date"]):
                title = e["title"]
                body = e.get("body", "")[:200].replace("\n", " ")
                earnings_lines.append(f"- **[{e['date']}] {title}.** {body} Tag: [Earnings]")
            result.append("")
            result.extend(earnings_lines)
            result.append("")
            injected = True

    return "\n".join(result)


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
