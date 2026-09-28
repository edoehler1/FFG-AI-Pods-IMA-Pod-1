"""
People Connector enricher — PwC engagement history per company.

Uses engagement_client_finder to surface who at PwC has worked with a target
company, the GRP, account team members, and recent engagement history.
Feeds into: profile_builder.py, company_analyzer.py, signal_matcher.py talking
points, weekly_report_agent.py.
"""

from ingestion.enrichment.base_enricher import BaseEnricher


class PeopleEngagementEnricher(BaseEnricher):
    mcp_source = "people_engagements"
    entity_type = "company"
    stale_days = 30

    def build_prompts(self, company) -> list[dict]:
        return [
            {
                "label": f"PwC engagement history for {company.name}",
                "prompt": (
                    f"Who at PwC has worked with {company.name}? "
                    f"Include the Global Relationship Partner (GRP), account team members, "
                    f"people who have billed time to engagements for this company, "
                    f"and any recent engagement history. "
                    f"For key people, include their office location and seniority level."
                ),
                "mcp_tool": "engagement_client_finder",
            },
        ]
