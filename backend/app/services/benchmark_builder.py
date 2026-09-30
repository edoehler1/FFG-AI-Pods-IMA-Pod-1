"""
Industry Benchmark Builder — computes per-sector financial benchmarks.

Pulls SEC XBRL financials for every tracked company in a sector, computes
median/min/max/avg for key metrics, and stores company rankings.
This is the yardstick for all per-company financial analyses.
"""

import json
import statistics
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.financial_analysis import IndustryBenchmark

SECTOR_COMPANIES: dict[str, list[str]] = {
    "automotive": [
        "Ford Motor Company",
        "General Motors",
        "Tesla Inc",
        "Rivian Automotive",
        "Stellantis NV",
        "Aptiv",
        "Magna International",
    ],
    "aerospace_defense": [
        "Lockheed Martin",
        "Boeing Company",
        "RTX Corporation",
        "Northrop Grumman",
        "General Dynamics",
        "L3Harris Technologies",
    ],
    "energy": [
        "ExxonMobil",
        "Chevron Corporation",
        "Shell plc",
        "NextEra Energy",
        "Duke Energy",
        "Enbridge Inc",
    ],
}

BENCHMARK_METRICS = [
    "Revenue",
    "Operating Income",
    "Gross Profit",
    "Net Income",
    "R&D Expense",
    "SG&A",
    "Total Assets",
    "Stockholders Equity",
    "Long-Term Debt",
    "CapEx (PP&E)",
]


def _get_latest_fy(periods: list[dict]) -> dict | None:
    fy_periods = [p for p in periods if p["period"] == "FY"]
    if not fy_periods:
        return None
    fy_periods.sort(key=lambda x: x["end_date"], reverse=True)
    return fy_periods[0]


def _get_previous_fy(periods: list[dict]) -> dict | None:
    fy_periods = [p for p in periods if p["period"] == "FY"]
    if len(fy_periods) < 2:
        return None
    fy_periods.sort(key=lambda x: x["end_date"], reverse=True)
    return fy_periods[1]


def _compute_derived_metrics(company_data: dict) -> dict[str, float | None]:
    revenue = company_data.get("Revenue", {}).get("latest")
    operating_income = company_data.get("Operating Income", {}).get("latest")
    gross_profit = company_data.get("Gross Profit", {}).get("latest")
    rd_expense = company_data.get("R&D Expense", {}).get("latest")
    equity = company_data.get("Stockholders Equity", {}).get("latest")
    debt = company_data.get("Long-Term Debt", {}).get("latest")
    capex = company_data.get("CapEx (PP&E)", {}).get("latest")

    prev_revenue = company_data.get("Revenue", {}).get("previous")

    derived = {}
    if revenue and operating_income:
        derived["operating_margin_pct"] = round(operating_income / revenue * 100, 1)
    if revenue and gross_profit:
        derived["gross_margin_pct"] = round(gross_profit / revenue * 100, 1)
    if revenue and prev_revenue and prev_revenue != 0:
        derived["revenue_growth_yoy_pct"] = round((revenue - prev_revenue) / abs(prev_revenue) * 100, 1)
    if revenue and rd_expense:
        derived["rd_as_pct_revenue"] = round(rd_expense / revenue * 100, 1)
    if equity and debt is not None:
        if equity != 0:
            derived["debt_to_equity"] = round(debt / abs(equity), 2)
    if revenue and capex:
        derived["capex_as_pct_revenue"] = round(abs(capex) / revenue * 100, 1)

    return derived


def _collect_company_financials(company_name: str) -> dict | None:
    from ingestion.sources.sec_edgar import KNOWN_CIKS
    from ingestion.sources.sec_financials import fetch_company_financials

    cik = KNOWN_CIKS.get(company_name)
    if not cik:
        return None

    raw = fetch_company_financials(cik, company_name)
    if not raw:
        return None

    metrics = {}
    for metric_name in BENCHMARK_METRICS:
        if metric_name not in raw:
            continue
        periods = raw[metric_name]
        latest = _get_latest_fy(periods)
        previous = _get_previous_fy(periods)
        metrics[metric_name] = {
            "latest": latest["value"] if latest else None,
            "latest_date": latest["end_date"] if latest else None,
            "previous": previous["value"] if previous else None,
            "previous_date": previous["end_date"] if previous else None,
        }

    derived = _compute_derived_metrics(metrics)
    return {"raw_metrics": metrics, "derived_metrics": derived}


def build_industry_benchmark(industry: str) -> dict:
    companies = SECTOR_COMPANIES.get(industry)
    if not companies:
        raise ValueError(f"Unknown industry: {industry}. Valid: {list(SECTOR_COMPANIES.keys())}")

    company_data: dict[str, dict] = {}
    for name in companies:
        print(f"  Benchmark: fetching {name}...")
        data = _collect_company_financials(name)
        if data:
            company_data[name] = data
        else:
            print(f"  Benchmark: no data for {name}")

    if not company_data:
        return {"industry": industry, "company_count": 0, "metrics": {}, "rankings": {}}

    derived_keys = [
        "operating_margin_pct",
        "gross_margin_pct",
        "revenue_growth_yoy_pct",
        "rd_as_pct_revenue",
        "debt_to_equity",
        "capex_as_pct_revenue",
    ]

    aggregated_metrics = {}
    for key in derived_keys:
        values = []
        for name, data in company_data.items():
            val = data["derived_metrics"].get(key)
            if val is not None:
                values.append({"company": name, "value": val})

        if not values:
            continue

        nums = [v["value"] for v in values]
        aggregated_metrics[key] = {
            "median": round(statistics.median(nums), 2),
            "mean": round(statistics.mean(nums), 2),
            "min": round(min(nums), 2),
            "max": round(max(nums), 2),
            "count": len(nums),
        }

    for metric_name in ["Revenue", "Operating Income", "Net Income"]:
        values = []
        for name, data in company_data.items():
            val = data["raw_metrics"].get(metric_name, {}).get("latest")
            if val is not None:
                values.append({"company": name, "value": val})
        if not values:
            continue
        nums = [v["value"] for v in values]
        aggregated_metrics[f"{metric_name}_absolute"] = {
            "median": round(statistics.median(nums), 2),
            "mean": round(statistics.mean(nums), 2),
            "min": round(min(nums), 2),
            "max": round(max(nums), 2),
            "count": len(nums),
        }

    rankings: dict[str, list[dict]] = {}
    for key in derived_keys:
        entries = []
        for name, data in company_data.items():
            val = data["derived_metrics"].get(key)
            if val is not None:
                entries.append({"company": name, "value": val})
        if entries:
            higher_is_better = key != "debt_to_equity"
            entries.sort(key=lambda x: x["value"], reverse=higher_is_better)
            for i, entry in enumerate(entries):
                entry["rank"] = i + 1
            rankings[key] = entries

    fiscal_year = "FY2025"
    for data in company_data.values():
        rev_date = data["raw_metrics"].get("Revenue", {}).get("latest_date")
        if rev_date:
            fiscal_year = f"FY{rev_date[:4]}"
            break

    return {
        "industry": industry,
        "fiscal_year": fiscal_year,
        "company_count": len(company_data),
        "companies_included": list(company_data.keys()),
        "metrics": aggregated_metrics,
        "rankings": rankings,
        "company_details": {
            name: data["derived_metrics"] for name, data in company_data.items()
        },
    }


def generate_and_store_benchmark(db: Session, industry: str) -> IndustryBenchmark:
    benchmark_data = build_industry_benchmark(industry)

    existing = (
        db.query(IndustryBenchmark)
        .filter(IndustryBenchmark.industry == industry)
        .first()
    )
    if existing:
        existing.benchmark_data = json.dumps(benchmark_data)
        existing.fiscal_year = benchmark_data["fiscal_year"]
        existing.generated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    record = IndustryBenchmark(
        id=str(uuid.uuid4()),
        industry=industry,
        fiscal_year=benchmark_data["fiscal_year"],
        benchmark_data=json.dumps(benchmark_data),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_benchmark(db: Session, industry: str) -> dict | None:
    record = (
        db.query(IndustryBenchmark)
        .filter(IndustryBenchmark.industry == industry)
        .first()
    )
    if not record:
        return None
    return json.loads(record.benchmark_data)


def generate_all_benchmarks(db: Session) -> list[dict]:
    results = []
    for industry in SECTOR_COMPANIES:
        try:
            record = generate_and_store_benchmark(db, industry)
            data = json.loads(record.benchmark_data)
            results.append({
                "industry": industry,
                "status": "ok",
                "company_count": data["company_count"],
            })
        except Exception as e:
            results.append({"industry": industry, "status": f"error: {e}"})
    return results
