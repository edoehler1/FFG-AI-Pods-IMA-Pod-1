"""
Earnings enricher — quarterly earnings call transcripts and takeaways.

Queries: EPS actual vs expected, revenue, management outlook, executive quotes.
Feeds into: company_analyzer.py, profile_builder.py, weekly_report_agent.py
"""

from ingestion.enrichment.base_enricher import BaseEnricher


class EarningsEnricher(BaseEnricher):
    mcp_source = "earnings"
    entity_type = "company"
    stale_days = 90

    def build_prompts(self, company) -> list[dict]:
        return [
            {
                "label": f"Earnings call for {company.name}",
                "prompt": (
                    f"What were the key takeaways from {company.name}'s most recent quarterly "
                    f"earnings call? Include EPS actual versus expected and whether it was a beat "
                    f"or miss, quarterly revenue figures, management outlook and guidance, and "
                    f"notable executive quotes on strategy or operational priorities."
                ),
                "mcp_tool": "earnings_natural_query",
            },
        ]
