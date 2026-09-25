"""
IBISWorld enricher — industry and sector intelligence.

Runs per tracked industry (not per company). 3 calls total.
Queries: market size, outlook, SWOT, competitive landscape, cost structure, regulation.
Feeds into: profile_builder.py, weekly_report_agent.py
"""

from ingestion.enrichment.base_enricher import BaseEnricher

INDUSTRY_QUERIES = {
    "automotive": (
        "What is the current market size, growth outlook, and competitive landscape "
        "for the automotive industry in the US? Include SWOT analysis, key external "
        "drivers, supply chain dynamics, cost structure breakdown, and regulatory environment. "
        "Cover both traditional OEMs and the EV transition."
    ),
    "aerospace_defense": (
        "What is the current market size, growth outlook, and competitive landscape "
        "for the US aerospace and defense industry? Include SWOT analysis, key external "
        "drivers such as defense budgets and geopolitical factors, supply chain dynamics, "
        "cost structure, and regulatory environment including ITAR and export controls."
    ),
    "energy": (
        "What is the current market size, growth outlook, and competitive landscape "
        "for the US energy sector? Include SWOT analysis covering oil and gas, renewables, "
        "and utilities. Cover key external drivers such as energy transition, regulation "
        "(FERC, NERC, IRA), supply chain dynamics, and cost structure breakdown."
    ),
}


class IBISWorldEnricher(BaseEnricher):
    mcp_source = "ibis"
    entity_type = "industry"
    stale_days = 30

    def build_prompts(self, industry_slug: str) -> list[dict]:
        prompt_text = INDUSTRY_QUERIES.get(industry_slug)
        if not prompt_text:
            return []
        return [
            {
                "label": f"IBISWorld sector report for {industry_slug}",
                "prompt": prompt_text,
                "mcp_tool": "ibis_natural_query",
            },
        ]
