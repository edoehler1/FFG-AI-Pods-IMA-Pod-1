"""
Web search enricher — open web cross-checking and gap-filling.

Used on-demand for private companies or entities without SEC coverage.
Feeds into: onboarding, profile_builder.py
"""

from ingestion.enrichment.base_enricher import BaseEnricher


class WebEnricher(BaseEnricher):
    mcp_source = "web"
    entity_type = "company"
    stale_days = 30

    def build_prompts(self, company) -> list[dict]:
        return [
            {
                "label": f"Web search for {company.name}",
                "prompt": (
                    f"What is {company.name}? Include headquarters location, primary products "
                    f"and services, approximate revenue and employee count, recent strategic "
                    f"developments, and competitive positioning in the {company.industry or 'EFS'} sector."
                ),
                "mcp_tool": "web_natural_query",
            },
        ]
