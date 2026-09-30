"""
Financial Analysis Agent — generates per-company financial analyses
benchmarked against industry peers.

Compares last two fiscal years of SEC XBRL data, incorporates MCP
enrichments (CapIQ, earnings calls), and ranks against the industry
benchmark from benchmark_builder.py.
"""

import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.financial_analysis import FinancialAnalysis
from app.services.benchmark_builder import get_benchmark, _collect_company_financials
from app.services.enrichment_reader import get_enrichment_text
from app.services.llm_client import call_llm


def _format_metric(value: float | None) -> str:
    if value is None:
        return "N/A"
    if abs(value) >= 1e9:
        return f"${value / 1e9:,.1f}B"
    if abs(value) >= 1e6:
        return f"${value / 1e6:,.0f}M"
    return f"${value:,.0f}"


def _build_financials_section(company_data: dict) -> str:
    lines = []
    raw = company_data["raw_metrics"]
    derived = company_data["derived_metrics"]

    for metric_name in ["Revenue", "Operating Income", "Gross Profit", "Net Income"]:
        info = raw.get(metric_name)
        if not info or not info.get("latest"):
            continue
        latest = _format_metric(info["latest"])
        prev = _format_metric(info.get("previous"))
        date = info.get("latest_date", "")
        lines.append(f"- **{metric_name}:** {latest} (FY ending {date}) | Prior year: {prev}")

    if derived.get("operating_margin_pct") is not None:
        lines.append(f"- **Operating Margin:** {derived['operating_margin_pct']}%")
    if derived.get("gross_margin_pct") is not None:
        lines.append(f"- **Gross Margin:** {derived['gross_margin_pct']}%")
    if derived.get("revenue_growth_yoy_pct") is not None:
        lines.append(f"- **Revenue Growth YoY:** {derived['revenue_growth_yoy_pct']}%")
    if derived.get("rd_as_pct_revenue") is not None:
        lines.append(f"- **R&D as % of Revenue:** {derived['rd_as_pct_revenue']}%")
    if derived.get("debt_to_equity") is not None:
        lines.append(f"- **Debt/Equity:** {derived['debt_to_equity']}")
    if derived.get("capex_as_pct_revenue") is not None:
        lines.append(f"- **CapEx as % of Revenue:** {derived['capex_as_pct_revenue']}%")

    return "\n".join(lines) if lines else "No structured financial data available."


def _build_benchmark_section(company_name: str, company_data: dict, benchmark: dict) -> str:
    if not benchmark or not benchmark.get("rankings"):
        return "No industry benchmark available."

    lines = [f"Industry: {benchmark['industry']} | Companies: {benchmark['company_count']}"]
    rankings = benchmark["rankings"]
    metrics_agg = benchmark["metrics"]
    derived = company_data["derived_metrics"]

    metric_display = {
        "operating_margin_pct": "Operating Margin",
        "gross_margin_pct": "Gross Margin",
        "revenue_growth_yoy_pct": "Revenue Growth YoY",
        "rd_as_pct_revenue": "R&D as % Revenue",
        "debt_to_equity": "Debt/Equity",
        "capex_as_pct_revenue": "CapEx as % Revenue",
    }

    for key, label in metric_display.items():
        ranking_list = rankings.get(key, [])
        agg = metrics_agg.get(key, {})
        company_val = derived.get(key)
        if company_val is None or not ranking_list:
            continue

        rank_entry = next((r for r in ranking_list if r["company"] == company_name), None)
        rank_str = f"#{rank_entry['rank']}/{len(ranking_list)}" if rank_entry else "unranked"
        median = agg.get("median", "N/A")
        unit = "x" if key == "debt_to_equity" else "%"

        lines.append(f"- **{label}:** {company_val}{unit} (rank {rank_str}, industry median {median}{unit})")

    return "\n".join(lines)


def _normalize_industry(industry: str | None) -> str | None:
    if not industry:
        return None
    mapping = {
        "automotive": "automotive",
        "auto": "automotive",
        "aerospace": "aerospace_defense",
        "aerospace & defense": "aerospace_defense",
        "aerospace_defense": "aerospace_defense",
        "a&d": "aerospace_defense",
        "energy": "energy",
        "energy_utilities": "energy",
        "utilities": "energy",
    }
    return mapping.get(industry.lower(), industry.lower())


def generate_financial_analysis(db: Session, company: Company) -> FinancialAnalysis:
    company_data = _collect_company_financials(company.name)
    if not company_data:
        content = f"No SEC XBRL data available for {company.name}. This company may be a non-US filer or private."
        return _store_analysis(db, company.id, content, {}, {})

    industry_key = _normalize_industry(company.industry)
    benchmark = get_benchmark(db, industry_key) if industry_key else None

    financials_section = _build_financials_section(company_data)
    benchmark_section = _build_benchmark_section(company.name, company_data, benchmark)

    capiq = get_enrichment_text(db, "company", company.id, "capiq", max_age_days=90) or ""
    earnings = get_enrichment_text(db, "company", company.id, "earnings", max_age_days=90) or ""

    capiq_block = f"\n## Capital IQ Enrichment\n{capiq[:3000]}" if capiq else ""
    earnings_block = f"\n## Earnings Call Highlights\n{earnings[:3000]}" if earnings else ""

    prompt = f"""You are a senior financial analyst at Strategy& writing a financial analysis document.

Company: {company.name}
Industry: {company.industry or 'Unknown'}

## Financial Data (SEC XBRL — last two fiscal years)
{financials_section}

## Industry Benchmark
{benchmark_section}
{capiq_block}
{earnings_block}

---

Write the analysis in EXACTLY this format:

# {company.name} — Financial Analysis

## Revenue & Growth
FY numbers, YoY comparison. Reference the industry median and ranking.
"Revenue of $X represents Y% growth, vs the industry median of Z%."

## Profitability
Operating margin, gross margin, SG&A trends.
"Ranks Nth of N companies in the sector."

## Balance Sheet
Debt position, capex intensity. Is the company deleveraging or leveraging? Why?

## Peer Benchmark
Compare to the 2-3 closest peers from the benchmark data (similar revenue scale or same sub-sector).
Where does this company outperform? Underperform?

## Key Takeaway
One paragraph: what the numbers say about where this company is headed and what it means for S& engagement opportunities.

Keep it under 600 words. Use specific numbers from the data. Every claim must reference an actual figure."""

    content = call_llm(prompt, max_tokens=2000)
    if not content:
        content = f"Financial analysis generation requires Claude API. {company.name} operates in {company.industry or 'EFS'}."

    key_metrics = company_data["derived_metrics"]
    peer_comparison = {}
    if benchmark and benchmark.get("rankings"):
        peer_comparison = {
            k: next((r for r in v if r["company"] == company.name), None)
            for k, v in benchmark["rankings"].items()
        }

    return _store_analysis(db, company.id, content, key_metrics, peer_comparison)


def _store_analysis(
    db: Session,
    company_id: str,
    content: str,
    key_metrics: dict,
    peer_comparison: dict,
) -> FinancialAnalysis:
    fiscal_year = "FY2025"

    existing = (
        db.query(FinancialAnalysis)
        .filter(FinancialAnalysis.company_id == company_id)
        .first()
    )
    if existing:
        existing.content = content
        existing.key_metrics = json.dumps(key_metrics)
        existing.peer_comparison = json.dumps(peer_comparison)
        existing.fiscal_year = fiscal_year
        existing.generated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    record = FinancialAnalysis(
        id=str(uuid.uuid4()),
        company_id=company_id,
        fiscal_year=fiscal_year,
        content=content,
        key_metrics=json.dumps(key_metrics),
        peer_comparison=json.dumps(peer_comparison),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_financial_analysis(db: Session, company_id: str) -> FinancialAnalysis | None:
    return (
        db.query(FinancialAnalysis)
        .filter(FinancialAnalysis.company_id == company_id)
        .first()
    )
