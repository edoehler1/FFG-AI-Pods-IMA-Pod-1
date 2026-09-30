"""
Portfolio Report Builder — generates a combined briefing across multiple companies.

Pulls the latest weekly reports for selected companies and sends them to Claude
for a portfolio-level synthesis with cross-company themes and prioritized opportunities.
"""

from datetime import datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.weekly_report import WeeklyReport
from app.services.llm_client import call_llm


def generate_portfolio_report(
    db: Session,
    company_ids: list[str],
    days_back: int = 7,
) -> dict:
    cutoff = datetime.utcnow() - timedelta(days=days_back + 7)

    companies = db.query(Company).filter(Company.id.in_(company_ids)).all()
    if not companies:
        return {"markdown": "No companies selected.", "company_count": 0}

    company_sections = []
    for company in companies:
        report = (
            db.query(WeeklyReport)
            .filter(
                WeeklyReport.company_id == company.id,
                WeeklyReport.generated_at >= cutoff,
            )
            .order_by(desc(WeeklyReport.generated_at))
            .first()
        )

        if report and report.content:
            urgency = f" [URGENCY: {report.urgency}]" if report.urgency else ""
            company_sections.append(
                f"### {company.name} ({company.industry or 'EFS'} / {company.client_status}){urgency}\n"
                f"{report.content[:2000]}"
            )
        else:
            company_sections.append(
                f"### {company.name} ({company.industry or 'EFS'} / {company.client_status})\n"
                f"No weekly report available."
            )

    companies_text = "\n\n".join(company_sections)

    industries = set(c.industry for c in companies if c.industry)
    industry_label = ", ".join(sorted(industries)) if industries else "EFS"

    prompt = f"""You are a Strategy& intelligence director writing a weekly portfolio briefing for a partner covering {len(companies)} companies across {industry_label}.

Below are the individual weekly intelligence reports for each company. Your job: synthesize them into a single portfolio-level briefing that highlights cross-company patterns, prioritizes opportunities by urgency, and gives the partner a clear action plan for the week.

## INDIVIDUAL COMPANY REPORTS
{companies_text}

---

Write the portfolio briefing in EXACTLY this format:

# Portfolio Intelligence Briefing
**Period:** Past {days_back} days | **Companies:** {len(companies)} | **Sectors:** {industry_label}

## Executive Summary
3-4 sentences: what is the single most important thing across the portfolio this week? What should the partner focus on first?

## Top Opportunities (ranked by urgency)
For each opportunity identified across companies, ranked highest urgency first:
- **[Company] — Opportunity title** (Urgency: high/medium/low)
  One sentence: what it is, why now, who should act.

## Cross-Portfolio Themes
2-3 themes that span multiple companies. For each:
- **Theme name** — which companies it affects and the S& implication.

## Sector Highlights
One paragraph per sector represented, summarizing the macro context.

## Recommended Actions This Week
Bulleted list of specific actions the partner should take, with company names and contact names where available.

Keep under 800 words. Be specific — every recommendation names a company and a reason."""

    markdown = call_llm(prompt, max_tokens=3000)
    if not markdown:
        markdown = _fallback_report(companies, company_sections)

    return {
        "markdown": markdown,
        "company_count": len(companies),
        "industries": sorted(industries),
    }


def _fallback_report(companies: list[Company], sections: list[str]) -> str:
    lines = ["# Portfolio Intelligence Briefing\n"]
    lines.append(f"**Companies:** {len(companies)}\n")
    for section in sections:
        lines.append(section)
        lines.append("")
    return "\n".join(lines)
