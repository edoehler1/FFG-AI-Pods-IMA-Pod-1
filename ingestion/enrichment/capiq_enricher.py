"""
CapIQ enricher — S&P Capital IQ company financials.

Queries: revenue, margins, ROE, peer comparisons, named competitors, key developments.
Covers non-US filers that SEC XBRL misses (Stellantis, Shell, Honda, Enbridge).
Feeds into: profile_builder.py, financial_analyzer.py, company_analyzer.py
"""

from ingestion.enrichment.base_enricher import BaseEnricher


class CapIQEnricher(BaseEnricher):
    mcp_source = "capiq"
    entity_type = "company"
    stale_days = 90

    def build_prompts(self, company) -> list[dict]:
        return [
            {
                "label": f"CapIQ financials for {company.name}",
                "prompt": (
                    f"What are the revenue, operating margins, ROE, and key financial "
                    f"developments for {company.name} over the past 3 fiscal years? "
                    f"Include named competitors and peer comparisons if available."
                ),
                "mcp_tool": "capiq_natural_query",
            },
        ]
