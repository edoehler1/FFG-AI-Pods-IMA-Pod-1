"""
Factiva enricher — licensed Dow Jones press coverage.

Queries: recent news from Reuters, WSJ, FT, industry trades.
Feeds into: company_analyzer.py, weekly_report_agent.py, importance_score on signals.
"""

from ingestion.enrichment.base_enricher import BaseEnricher


class FactivaEnricher(BaseEnricher):
    mcp_source = "factiva"
    entity_type = "company"
    stale_days = 7

    def build_prompts(self, company, days: int = 30) -> list[dict]:
        return [
            {
                "label": f"Factiva news for {company.name}",
                "prompt": (
                    f"What is the latest news on {company.name} in the past {days} days? "
                    f"Focus on strategic moves, M&A activity, leadership changes, regulatory "
                    f"actions, earnings announcements, and operational developments. Exclude "
                    f"consumer product reviews and entertainment coverage."
                ),
                "mcp_tool": "factiva_natural_query",
            },
        ]
