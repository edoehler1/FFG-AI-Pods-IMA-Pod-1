from datetime import datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings
from app.models.company import Company
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch


def gather_report_data(
    db: Session,
    industry: str | None = None,
    client_status: str | None = None,
    days: int = 7,
) -> dict:
    now = datetime.utcnow()
    cutoff = now - timedelta(days=days)

    company_query = db.query(Company)
    if industry:
        company_query = company_query.filter(Company.industry == industry)
    if client_status:
        company_query = company_query.filter(Company.client_status == client_status)
    companies = company_query.all()

    company_signals = {}
    unmatched_signals = []

    matched_company_ids = {c.id for c in companies}
    matches = (
        db.query(SignalCompanyMatch)
        .filter(SignalCompanyMatch.company_id.in_(matched_company_ids))
        .all()
    )

    signal_to_companies: dict[str, list[str]] = {}
    for m in matches:
        signal_to_companies.setdefault(m.signal_id, []).append(m.company_id)

    matched_signal_ids = list(signal_to_companies.keys())
    signals = (
        db.query(Signal)
        .filter(Signal.id.in_(matched_signal_ids))
        .order_by(desc(Signal.published_at))
        .all()
    ) if matched_signal_ids else []

    company_id_to_name = {}
    company_map = {c.id: c for c in companies}
    for signal in signals:
        for cid in signal_to_companies.get(signal.id, []):
            company = company_map.get(cid)
            if company:
                company_id_to_name[company.name] = company.id
                company_signals.setdefault(company.name, []).append({
                    "title": signal.title,
                    "industry": signal.industry,
                    "sub_sector": signal.sub_sector,
                    "signal_type": signal.signal_type,
                    "published_at": str(signal.published_at) if signal.published_at else None,
                    "url": signal.url,
                    "body": (signal.body or "")[:300],
                })

    recent_unmatched = (
        db.query(Signal)
        .filter(Signal.published_at >= cutoff if cutoff else True)
        .filter(~Signal.id.in_(matched_signal_ids) if matched_signal_ids else True)
        .order_by(desc(Signal.published_at))
        .limit(10)
        .all()
    )

    return {
        "company_count": len(companies),
        "total_matched_signals": len(signals),
        "period_days": days,
        "period_start": cutoff.strftime("%B %d, %Y"),
        "period_end": now.strftime("%B %d, %Y"),
        "company_signals": company_signals,
        "unmatched_highlights": [
            {"title": s.title, "industry": s.industry, "sub_sector": s.sub_sector, "url": s.url}
            for s in recent_unmatched
        ],
        "company_id_map": company_id_to_name,
        "db": db,
    }


def generate_report_with_llm(report_data: dict) -> str:
    from app.services.llm_client import is_llm_available, call_llm

    if not is_llm_available():
        return _generate_template_report(report_data)

    from app.services.enrichment_reader import get_enrichment_text

    db = report_data.get("db")
    company_id_map = report_data.get("company_id_map", {})

    company_sections = []
    for company, signals in report_data["company_signals"].items():
        signal_list = "\n".join(
            f"  - [{s['signal_type']}] {s['title']}" + (f" ({s['sub_sector']})" if s['sub_sector'] else "")
            for s in signals[:5]
        )
        enrichment_line = ""
        cid = company_id_map.get(company)
        if db and cid:
            factiva = get_enrichment_text(db, "company", cid, "factiva", max_age_days=14)
            if factiva:
                enrichment_line = f"\n  Licensed Press Context: {factiva[:400]}"
        company_sections.append(f"**{company}** ({len(signals)} signals):\n{signal_list}{enrichment_line}")

    unmatched_list = "\n".join(
        f"  - {s['title']} ({s['industry']}, {s['sub_sector'] or 'general'})"
        for s in report_data["unmatched_highlights"][:10]
    )

    prompt = f"""You are a Strategy& intelligence analyst writing a weekly signal brief for an EFS (Energy, Aerospace & Defense, Automotive) partner.

Based on the following matched signals for their portfolio companies, write a concise, actionable weekly brief. For each company with signals, summarize what happened and suggest what the partner should do (reach out, monitor, prepare a pitch, etc.).

End with a "Discovery" section highlighting unmatched signals that could represent new opportunities.

Keep the tone professional but direct — this is for a busy partner who needs to scan it in 2 minutes. Use the exact dates provided below — never write placeholders like "[current week]".

## Portfolio Signals — {report_data['period_start']} to {report_data['period_end']} ({report_data['total_matched_signals']} signals across {report_data['company_count']} companies)

{chr(10).join(company_sections) if company_sections else "No matched signals this period."}

## Unmatched Signals (potential new opportunities)
{unmatched_list if unmatched_list else "None this period."}

Write the brief now. Use markdown formatting with headers for each company."""

    result = call_llm(prompt, max_tokens=2000)
    return result if result else _generate_template_report(report_data)


def _generate_template_report(report_data: dict) -> str:
    lines = [
        f"# Weekly Signal Brief",
        f"",
        f"**Period:** {report_data['period_start']} — {report_data['period_end']} | "
        f"**Companies:** {report_data['company_count']} | "
        f"**Matched Signals:** {report_data['total_matched_signals']}",
        f"",
        f"---",
        f"",
        f"## Portfolio Updates",
        f"",
    ]

    if not report_data["company_signals"]:
        lines.append("No matched signals this period.\n")
    else:
        for company, signals in report_data["company_signals"].items():
            lines.append(f"### {company} ({len(signals)} signal{'s' if len(signals) != 1 else ''})")
            lines.append("")
            for s in signals[:5]:
                sub = f" *({s['sub_sector']})*" if s["sub_sector"] else ""
                lines.append(f"- **[{s['signal_type']}]** {s['title']}{sub}")
            if len(signals) > 5:
                lines.append(f"- *...and {len(signals) - 5} more*")
            lines.append("")

    lines.extend([
        "---",
        "",
        "## Discovery — Potential New Opportunities",
        "",
    ])

    if not report_data["unmatched_highlights"]:
        lines.append("No unmatched signals this period.\n")
    else:
        for s in report_data["unmatched_highlights"]:
            industry = s["industry"] or "general"
            sub = f", {s['sub_sector']}" if s["sub_sector"] else ""
            lines.append(f"- {s['title']} *(industry: {industry}{sub})*")
        lines.append("")

    return "\n".join(lines)
