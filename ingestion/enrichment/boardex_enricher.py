"""
BoardEx enricher — executive and board intelligence.

Queries: C-suite roster, board composition, recent leadership changes, employment history.
Feeds into: profile_builder.py, weekly_report_agent.py, executive intelligence views.
"""

from ingestion.enrichment.base_enricher import BaseEnricher


class BoardExEnricher(BaseEnricher):
    mcp_source = "boardex"
    entity_type = "company"
    stale_days = 30

    def build_prompts(self, company) -> list[dict]:
        return [
            {
                "label": f"BoardEx executives for {company.name}",
                "prompt": (
                    f"Who are the current C-suite executives and board members at {company.name}? "
                    f"Include any recent leadership changes, board appointments, or resignations "
                    f"in the past 12 months. For key executives, include their employment history "
                    f"and education background."
                ),
                "mcp_tool": "boardex_natural_query",
            },
        ]
