"""
CLI runner for MCP enrichment.

This script is the companion to ingestion/run.py. It must be run within a
Claude Code session because the actual MCP calls are made by Claude, not by
this script directly. The workflow:

1. This script reads companies/industries from the database.
2. For each entity, it checks staleness and builds the MCP prompt.
3. It prints the prompts that need to be executed.
4. Claude calls the MCP tools and stores results via the API or directly.

Usage:
    python -m ingestion.enrich                              # List all needed enrichments
    python -m ingestion.enrich --mcp capiq                  # One MCP source only
    python -m ingestion.enrich --company "Boeing Company"   # One company only
    python -m ingestion.enrich --industry automotive        # One industry only
    python -m ingestion.enrich --force                      # Ignore staleness, refresh all
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ingestion.config import DATABASE_URL
from app.database import Base
from app.models.company import Company
from app.models.mcp_enrichment import MCPEnrichment  # noqa: F401

from ingestion.enrichment.capiq_enricher import CapIQEnricher
from ingestion.enrichment.boardex_enricher import BoardExEnricher
from ingestion.enrichment.earnings_enricher import EarningsEnricher
from ingestion.enrichment.emis_enricher import EMISEnricher
from ingestion.enrichment.ibis_enricher import IBISWorldEnricher
from ingestion.enrichment.factiva_enricher import FactivaEnricher
from ingestion.enrichment.web_enricher import WebEnricher
from ingestion.enrichment.sec_mcp_enricher import SECRiskEnricher, SECMDAEnricher
from ingestion.enrichment.thought_leadership_enricher import (
    ConnectedSourceEnricher,
    VIMEnricher,
    CEOSurveyEnricher,
)
from ingestion.enrichment.salesforce_enricher import SalesforceEnricher
from ingestion.enrichment.people_connector_enricher import PeopleEngagementEnricher

COMPANY_ENRICHERS = {
    "capiq": CapIQEnricher(),
    "boardex": BoardExEnricher(),
    "earnings": EarningsEnricher(),
    "emis": EMISEnricher(),
    "factiva": FactivaEnricher(),
    "web": WebEnricher(),
    "sec_mcp_risk": SECRiskEnricher(),
    "sec_mcp_mda": SECMDAEnricher(),
    "salesforce": SalesforceEnricher(),
    "people_engagements": PeopleEngagementEnricher(),
}

INDUSTRY_ENRICHERS = {
    "ibis": IBISWorldEnricher(),
    "connectedsource": ConnectedSourceEnricher(),
    "vim": VIMEnricher(),
    "ceo_survey": CEOSurveyEnricher(),
}

TRACKED_INDUSTRIES = ["automotive", "aerospace_defense", "energy"]


def list_needed_enrichments(
    session,
    mcp_filter: str | None = None,
    company_filter: str | None = None,
    industry_filter: str | None = None,
    force: bool = False,
):
    tasks = []

    company_sources = COMPANY_ENRICHERS
    if mcp_filter and mcp_filter in COMPANY_ENRICHERS:
        company_sources = {mcp_filter: COMPANY_ENRICHERS[mcp_filter]}
    elif mcp_filter and mcp_filter not in COMPANY_ENRICHERS and mcp_filter not in INDUSTRY_ENRICHERS:
        print(f"Unknown MCP source: {mcp_filter}")
        print(f"Available: {', '.join(list(COMPANY_ENRICHERS) + list(INDUSTRY_ENRICHERS))}")
        return tasks

    if not mcp_filter or mcp_filter in COMPANY_ENRICHERS:
        query = session.query(Company)
        if company_filter:
            query = query.filter(Company.name.ilike(f"%{company_filter}%"))
        companies = query.all()

        for company in companies:
            for source_name, enricher in company_sources.items():
                if force or enricher.should_refresh(session, company.id):
                    prompts = enricher.build_prompts(company)
                    for p in prompts:
                        tasks.append({
                            "entity_type": "company",
                            "entity_id": company.id,
                            "entity_name": company.name,
                            "mcp_source": source_name,
                            "mcp_tool": p["mcp_tool"],
                            "label": p["label"],
                            "prompt": p["prompt"],
                        })

    industry_sources = INDUSTRY_ENRICHERS
    if mcp_filter and mcp_filter in INDUSTRY_ENRICHERS:
        industry_sources = {mcp_filter: INDUSTRY_ENRICHERS[mcp_filter]}

    if not mcp_filter or mcp_filter in INDUSTRY_ENRICHERS:
        industries = TRACKED_INDUSTRIES
        if industry_filter:
            industries = [i for i in TRACKED_INDUSTRIES if industry_filter in i]

        for industry in industries:
            for source_name, enricher in industry_sources.items():
                if force or enricher.should_refresh(session, industry):
                    prompts = enricher.build_prompts(industry)
                    for p in prompts:
                        tasks.append({
                            "entity_type": "industry",
                            "entity_id": industry,
                            "entity_name": industry,
                            "mcp_source": source_name,
                            "mcp_tool": p["mcp_tool"],
                            "label": p["label"],
                            "prompt": p["prompt"],
                        })

    return tasks


def main():
    parser = argparse.ArgumentParser(description="List MCP enrichment tasks")
    parser.add_argument("--mcp", type=str, help="Specific MCP source to run")
    parser.add_argument("--company", type=str, help="Filter to one company (name search)")
    parser.add_argument("--industry", type=str, help="Filter to one industry")
    parser.add_argument("--force", action="store_true", help="Ignore staleness, refresh all")
    args = parser.parse_args()

    connect_args = {}
    if DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        tasks = list_needed_enrichments(
            session,
            mcp_filter=args.mcp,
            company_filter=args.company,
            industry_filter=args.industry,
            force=args.force,
        )

        if not tasks:
            print("All enrichments are up to date. Use --force to refresh.")
            return

        print(f"\n{len(tasks)} enrichment tasks needed:\n")

        by_source = {}
        for t in tasks:
            by_source.setdefault(t["mcp_source"], []).append(t)

        for source, source_tasks in by_source.items():
            print(f"  [{source}] — {len(source_tasks)} calls")
            for t in source_tasks[:3]:
                print(f"    • {t['label']}")
            if len(source_tasks) > 3:
                print(f"    ... and {len(source_tasks) - 3} more")

        print(f"\nTo execute: Claude should call each MCP tool with the listed prompts")
        print(f"and store results via POST /api/enrichments or enricher.store_result().")

    finally:
        session.close()


if __name__ == "__main__":
    main()
