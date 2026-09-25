"""
Thought Leadership enricher — PwC Connected Sources, VIM, CEO Survey.

Runs per tracked industry (not per company).
Connected Sources: PwC industry insights and POVs (passage search, returns excerpts).
VIM: Value in Motion — how value is shifting across industries.
CEO Survey: CEO sentiment, confidence, AI adoption, workforce priorities.
Feeds into: signal_matcher.py talking points, profile_builder.py, weekly_report_agent.py
"""

from ingestion.enrichment.base_enricher import BaseEnricher

INDUSTRY_LABELS = {
    "automotive": "automotive industry, electric vehicle transition, and mobility transformation",
    "aerospace_defense": "aerospace and defense industry, defense procurement, and space sector",
    "energy": "energy sector, energy transition, renewables, oil and gas, and utilities",
}


class ConnectedSourceEnricher(BaseEnricher):
    mcp_source = "connectedsource"
    entity_type = "industry"
    stale_days = 30

    def build_prompts(self, industry_slug: str) -> list[dict]:
        label = INDUSTRY_LABELS.get(industry_slug, industry_slug)
        return [
            {
                "label": f"PwC insights for {industry_slug}",
                "prompt": (
                    f"What are PwC's latest insights on the {label}? "
                    f"Include points of view on industry trends, market developments, "
                    f"transformation themes, and strategic priorities for companies in this sector."
                ),
                "mcp_tool": "connectedsource_natural_query",
            },
        ]


class VIMEnricher(BaseEnricher):
    mcp_source = "vim"
    entity_type = "industry"
    stale_days = 90

    def build_prompts(self, industry_slug: str) -> list[dict]:
        label = INDUSTRY_LABELS.get(industry_slug, industry_slug)
        return [
            {
                "label": f"VIM value shifts for {industry_slug}",
                "prompt": (
                    f"How is value shifting across the {label} under technology disruption, "
                    f"regulation, and changing consumer behavior? What are the specific "
                    f"Value in Motion domains and opportunities that apply?"
                ),
                "mcp_tool": "vim_natural_query",
            },
        ]


class CEOSurveyEnricher(BaseEnricher):
    mcp_source = "ceo_survey"
    entity_type = "industry"
    stale_days = 180

    def build_prompts(self, industry_slug: str) -> list[dict]:
        label = INDUSTRY_LABELS.get(industry_slug, industry_slug)
        return [
            {
                "label": f"CEO Survey for {industry_slug}",
                "prompt": (
                    f"What do CEOs in the {label} say about revenue growth confidence, "
                    f"business reinvention, generative AI adoption, workforce priorities, "
                    f"and climate action? Include specific percentages and year-over-year "
                    f"comparisons where available."
                ),
                "mcp_tool": "ceo_natural_query",
            },
        ]
