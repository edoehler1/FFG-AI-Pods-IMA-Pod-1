"""
Salesforce enricher — advisory/strategy CRM pipeline and opportunity data.

Queries: open advisory/consulting/strategy opportunities only.
Excludes: audit, tax, assurance engagements.
Feeds into: profile_builder.py, company_analyzer.py, weekly_report_agent.py, dashboard.
"""

import json
import re

from ingestion.enrichment.base_enricher import BaseEnricher


class SalesforceEnricher(BaseEnricher):
    mcp_source = "salesforce"
    entity_type = "company"
    stale_days = 7

    def build_prompts(self, company) -> list[dict]:
        return [
            {
                "label": f"Salesforce advisory pipeline for {company.name}",
                "prompt": (
                    f"Give me the latest advisory and strategy consulting pipeline on {company.name}. "
                    f"Show only advisory, strategy, consulting, and management consulting opportunities — "
                    f"exclude any audit, tax, assurance, or attestation engagements. "
                    f"For each opportunity show: opportunity name, deal stage, expected close date, "
                    f"opportunity value/amount, and opportunity owner. "
                    f"Include total advisory pipeline value if available."
                ),
                "mcp_tool": "salesforce_natural_query",
            },
        ]

    def store_result(self, db, entity_id, prompt, markdown, summary=None, citations=None):
        parsed = _parse_opportunities(markdown)
        if parsed["opportunities"]:
            summary = parsed
        return super().store_result(db, entity_id, prompt, markdown, summary=summary, citations=citations)


def _parse_opportunities(markdown: str) -> dict:
    opportunities = []
    total_value = None

    total_match = re.search(
        r"total\s+(?:advisory\s+)?pipeline\s+(?:value\s+)?(?:of\s+)?\$?([\d,.]+)\s*(M|million|B|billion|K|thousand)?",
        markdown, re.IGNORECASE,
    )
    if total_match:
        raw = total_match.group(1).replace(",", "")
        multiplier_str = (total_match.group(2) or "").lower()
        multipliers = {"m": 1_000_000, "million": 1_000_000, "b": 1_000_000_000, "billion": 1_000_000_000, "k": 1_000, "thousand": 1_000}
        multiplier = multipliers.get(multiplier_str, 1)
        try:
            total_value = float(raw) * multiplier
        except ValueError:
            pass

    opp_patterns = [
        re.compile(r"\*\*(.+?)\*\*.*?\$?([\d,.]+)\s*(M|million|B|billion|K|thousand)?.*?([\w\s]+stage|closed|won|lost|proposal|negotiation|qualification)", re.IGNORECASE),
        re.compile(r"[-•]\s*(.+?)\s*[-–—]\s*\$?([\d,.]+)\s*(M|million|K|thousand)?.*?([\w\s]+stage|closed|won|lost|proposal|negotiation|qualification)", re.IGNORECASE),
    ]

    for pattern in opp_patterns:
        for match in pattern.finditer(markdown):
            name = match.group(1).strip()[:200]
            raw_val = match.group(2).replace(",", "")
            mult_str = (match.group(3) or "").lower()
            mults = {"m": 1_000_000, "million": 1_000_000, "b": 1_000_000_000, "billion": 1_000_000_000, "k": 1_000, "thousand": 1_000}
            mult = mults.get(mult_str, 1)
            try:
                value = float(raw_val) * mult
            except ValueError:
                value = None
            stage = match.group(4).strip()

            opportunities.append({
                "name": name,
                "value": value,
                "stage": stage,
            })

    close_dates = re.findall(
        r"(?:close|expected|closing)\s+(?:date)?:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})",
        markdown, re.IGNORECASE,
    )

    for i, date_str in enumerate(close_dates):
        if i < len(opportunities):
            opportunities[i]["close_date"] = date_str.strip()

    owner_matches = re.findall(
        r"(?:owner|lead|assigned\s+to):?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        markdown,
    )
    for i, owner in enumerate(owner_matches):
        if i < len(opportunities):
            opportunities[i]["owner"] = owner.strip()

    opp_count = len(opportunities)
    summary_text = f"{opp_count} advisory opportunity{'s' if opp_count != 1 else ''}"
    if total_value:
        if total_value >= 1_000_000:
            summary_text += f", ${total_value / 1_000_000:.1f}M total pipeline"
        elif total_value >= 1_000:
            summary_text += f", ${total_value / 1_000:.0f}K total pipeline"
        else:
            summary_text += f", ${total_value:,.0f} total pipeline"

    nearest_close = None
    for opp in opportunities:
        if opp.get("close_date"):
            nearest_close = opp["close_date"]
            break
    if nearest_close:
        summary_text += f". Nearest close: {nearest_close}"

    return {
        "summary_text": summary_text,
        "total_pipeline_value": total_value,
        "opportunity_count": opp_count,
        "opportunities": opportunities,
    }
