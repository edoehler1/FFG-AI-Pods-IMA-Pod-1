"""
Store People Connector enrichment for all companies using the Aptiv format.
Uses pre-downloaded MCP JSON files where available.
"""

import json
import sys
import os
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from parse_engagement_data import parse_engagement_file, parse_engagement_data, build_markdown, apply_email_lookups
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.mcp_enrichment import MCPEnrichment
from app.models.company import Company

engine = create_engine("sqlite:///data/signals.db", connect_args={"check_same_thread": False})
db = sessionmaker(bind=engine)()

TOOL_RESULTS_DIR = r"C:\Users\gsolis014\.claude\projects\C--Projects-FFG-AI-Pods-IMA-Pod-1\e47d6fa2-e2c5-47a8-b52b-2eb2a0aaa6e0\tool-results"

# Map company names to their MCP result files (already downloaded)
FILE_MAP = {
    "Boeing Company": "mcp-people-connector-tools-gateway-engagement_client_finder-1790635245398.txt",
    "Lockheed Martin": "mcp-people-connector-tools-gateway-engagement_client_finder-1790635246281.txt",
    "General Motors": "toolu_bdrk_01DkfNbe8QLzeK6KfPmm68UQ.txt",
    "Northrop Grumman": "toolu_bdrk_01LoYnGCPnw6ucPzaFcrzrR1.txt",
    "General Dynamics": "mcp-people-connector-tools-gateway-engagement_client_finder-1790635308728.txt",
    "L3Harris Technologies": "toolu_bdrk_01JVxXvrw3GGkBKP8tfuwo8G.txt",
}

# Skip these (already done correctly in Aptiv format)
SKIP = {"Aptiv", "Ford Motor Company"}

companies = db.query(Company).order_by(Company.industry, Company.name).all()

for company in companies:
    if company.name in SKIP:
        print(f"[SKIP] {company.name} — already in Aptiv format")
        continue

    filepath = None
    if company.name in FILE_MAP:
        filepath = os.path.join(TOOL_RESULTS_DIR, FILE_MAP[company.name])
        if not os.path.exists(filepath):
            print(f"[MISSING FILE] {company.name} — {filepath}")
            continue

    if not filepath:
        print(f"[NO DATA] {company.name} — no MCP file downloaded yet")
        continue

    print(f"[PROCESSING] {company.name}...")
    summary = parse_engagement_file(filepath)
    markdown = build_markdown(summary, company.name)

    # Upsert
    existing = db.query(MCPEnrichment).filter(
        MCPEnrichment.entity_type == "company",
        MCPEnrichment.entity_id == company.id,
        MCPEnrichment.mcp_source == "people_engagements",
    ).first()

    now = datetime.utcnow()
    if existing:
        existing.response_markdown = markdown
        existing.response_summary = json.dumps(summary)
        existing.fetched_at = now
    else:
        db.add(MCPEnrichment(
            id=str(uuid.uuid4()),
            entity_type="company",
            entity_id=company.id,
            mcp_source="people_engagements",
            query_prompt=f"PwC advisory engagement history for {company.name}",
            response_markdown=markdown,
            response_summary=json.dumps(summary),
            fetched_at=now,
            stale_after=now + timedelta(days=30),
        ))

    db.commit()

    open_count = sum(1 for e in summary["engagements"] if e["status"] == "open")
    strategy_count = sum(1 for e in summary["engagements"] if "strategy" in (e.get("service_line") or "").lower() or "strategy" in (e.get("name") or "").lower())
    grp_name = summary["grp"]["name"] if summary.get("grp") else "none"
    print(f"  GRP: {grp_name} | {len(summary['engagements'])} engagements ({open_count} open) | {len(summary['engagement_staff'])} senior staff")

db.close()
print("\nDone.")
