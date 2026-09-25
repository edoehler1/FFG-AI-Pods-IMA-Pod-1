"""
EMIS enricher — ownership structure and corporate hierarchy.

Queries: major shareholders, ownership %, subsidiaries, affiliates.
Feeds into: profile_builder.py
"""

from ingestion.enrichment.base_enricher import BaseEnricher


class EMISEnricher(BaseEnricher):
    mcp_source = "emis"
    entity_type = "company"
    stale_days = 90

    def build_prompts(self, company) -> list[dict]:
        return [
            {
                "label": f"EMIS ownership for {company.name}",
                "prompt": (
                    f"What is the ownership structure of {company.name}? Include major shareholders "
                    f"and their ownership percentages, key subsidiaries and affiliates, and any "
                    f"recent changes in ownership or corporate structure."
                ),
                "mcp_tool": "emis_natural_query",
            },
        ]
