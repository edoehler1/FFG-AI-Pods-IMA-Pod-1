"""
Salesforce enricher — CRM pipeline and opportunity data.

Queries: open opportunities, deal stages, close dates, recent activity.
Feeds into: profile_builder.py, company_analyzer.py, signal_matcher.py talking points.
"""

from ingestion.enrichment.base_enricher import BaseEnricher


class SalesforceEnricher(BaseEnricher):
    mcp_source = "salesforce"
    entity_type = "company"
    stale_days = 7

    def build_prompts(self, company) -> list[dict]:
        return [
            {
                "label": f"Salesforce pipeline for {company.name}",
                "prompt": (
                    f"Give me the latest pipeline on {company.name}. "
                    f"Show open opportunities, deal stages, expected close dates, "
                    f"opportunity owners, and any recent activity or notes. "
                    f"Include total pipeline value if available."
                ),
                "mcp_tool": "salesforce_natural_query",
            },
        ]
