"""
SEC MCP enrichers — filing content analysis (risk factors, MD&A).

Split into two enrichers with distinct mcp_source values to avoid upsert
collision in the mcp_enrichments table.

Complements existing sec_edgar.py (metadata) and sec_financials.py (XBRL numbers)
by reading actual filing content.
Feeds into: profile_builder.py, company_analyzer.py, financial_analyzer.py
"""

from ingestion.enrichment.base_enricher import BaseEnricher


class SECRiskEnricher(BaseEnricher):
    mcp_source = "sec_mcp_risk"
    entity_type = "company"
    stale_days = 90

    def build_prompts(self, company) -> list[dict]:
        return [
            {
                "label": f"SEC risk factors for {company.name}",
                "prompt": (
                    f"What are the key risk factors disclosed in {company.name}'s most recent "
                    f"10-K annual report? Summarize the top 5-7 most material risks."
                ),
                "mcp_tool": "sec_natural_query",
            },
        ]


class SECMDAEnricher(BaseEnricher):
    mcp_source = "sec_mcp_mda"
    entity_type = "company"
    stale_days = 90

    def build_prompts(self, company) -> list[dict]:
        return [
            {
                "label": f"SEC MD&A for {company.name}",
                "prompt": (
                    f"What does {company.name}'s most recent 10-K or 10-Q say in the "
                    f"Management's Discussion and Analysis (MD&A) section about revenue trends, "
                    f"operational challenges, and strategic priorities?"
                ),
                "mcp_tool": "sec_natural_query",
            },
        ]
