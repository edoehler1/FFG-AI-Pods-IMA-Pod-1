"""
Portfolio Report Builder — card-based portfolio briefing.

Pulls each company's weekly briefing card summary and arranges them by
confidence tier. Adds cross-portfolio themes via a short Claude call.
No prose essay — structured cards a partner can scan in 30 seconds.
"""

import json
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
        return {"cards": [], "themes": [], "actions": [], "company_count": 0, "industries": []}

    company_map = {c.id: c for c in companies}
    cards = []
    headlines_for_themes = []

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

        card_data = None
        if report and report.opportunity_summary:
            try:
                card_data = json.loads(report.opportunity_summary)
            except (json.JSONDecodeError, TypeError):
                pass

        if card_data and card_data.get("headline"):
            card = {
                "company_name": company.name,
                "company_id": company.id,
                "industry": company.industry,
                "client_status": company.client_status,
                "headline": card_data.get("headline", ""),
                "confidence_score": card_data.get("confidence_score", 0),
                "confidence_tier": card_data.get("confidence_tier", "Noted"),
                "opportunity": card_data.get("opportunity", ""),
                "taxonomy_tag": card_data.get("taxonomy_tag", ""),
                "action": card_data.get("action", ""),
                "week_start": report.week_start,
                "week_end": report.week_end,
                "signal_count": report.signal_count or 0,
            }
            cards.append(card)
            headlines_for_themes.append(
                f"- {company.name} ({company.industry}): {card_data.get('headline', '')}"
            )
        else:
            cards.append({
                "company_name": company.name,
                "company_id": company.id,
                "industry": company.industry,
                "client_status": company.client_status,
                "headline": "No briefing generated yet — generate from the company page.",
                "confidence_score": 0,
                "confidence_tier": "Noted",
                "opportunity": "",
                "taxonomy_tag": "",
                "action": "",
                "week_start": "",
                "week_end": "",
                "signal_count": 0,
            })

    cards.sort(key=lambda c: c["confidence_score"], reverse=True)

    industries = sorted(set(c.industry for c in companies if c.industry))

    themes, actions = _get_cross_portfolio_themes(headlines_for_themes, industries)

    return {
        "cards": cards,
        "themes": themes,
        "actions": actions,
        "company_count": len(companies),
        "industries": industries,
    }


def _get_cross_portfolio_themes(headlines: list[str], industries: list[str]) -> tuple[list[str], list[str]]:
    if not headlines:
        return [], []

    prompt = f"""Given these company headlines from a weekly portfolio briefing:

{chr(10).join(headlines)}

Sectors covered: {', '.join(industries)}

Provide:
1. THEMES: 2-3 cross-portfolio themes (patterns that span multiple companies). Each one sentence.
2. ACTIONS: 3-5 specific actions for the partner this week. Each one sentence naming a company.

Return ONLY valid JSON:
{{"themes": ["theme 1", "theme 2"], "actions": ["action 1", "action 2", "action 3"]}}"""

    response = call_llm(prompt, max_tokens=800)
    if not response:
        return ["Multiple companies showing strategic inflection points this week."], ["Review individual company briefings for detailed actions."]

    try:
        import re
        cleaned = re.sub(r"```\w*\s*", "", response.strip()).strip()
        data = json.loads(cleaned)
        return data.get("themes", []), data.get("actions", [])
    except (json.JSONDecodeError, KeyError):
        return ["Multiple companies showing strategic inflection points this week."], ["Review individual company briefings for detailed actions."]
