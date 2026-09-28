import json, sys, os, uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.mcp_enrichment import MCPEnrichment

engine = create_engine("sqlite:///data/signals.db", connect_args={"check_same_thread": False})
db = sessionmaker(bind=engine)()

COMPANY_ID = "8ed5bc5b-ff1c-4e16-800a-4c6152034024"

engagements = [
    {
        "name": "Magna - OneStream ESG Planning & Blueprint",
        "service_line": "FP&A Tech - Enabling Apps",
        "description": "OneStream ESG planning and reporting implementation. Phase 1 blueprint and configuration.",
        "start_date": "2026-03-02", "end_date": "2026-05-29", "status": "closed",
        "staff_count": 5,
        "key_staff": [
            {"name": "Leonardo De Biasi", "role": "Principal, Engagement Leader", "email": "leonardo.debiasi@pwc.com"},
            {"name": "Will Chen", "role": "Director", "email": "will.chen@pwc.com"},
        ],
    },
    {
        "name": "Magna International - SSB Phase 0 Planning",
        "service_line": "Finance Operations - Process Support",
        "description": "Shared services benchmarking and phase 0 planning for finance operations.",
        "start_date": "2025-12-01", "end_date": "2025-12-31", "status": "closed",
        "staff_count": 1,
        "key_staff": [
            {"name": "Nitin Bansal", "role": "Director, Engagement Manager", "email": "bansal.nitin@pwc.com"},
        ],
    },
    {
        "name": "GBS Location Tool Support",
        "service_line": "Finance Function Strategy",
        "description": "Global business services location strategy and tool support for Canadian operations.",
        "start_date": "2025-10-22", "end_date": "2025-11-07", "status": "closed",
        "staff_count": 2,
        "key_staff": [],
    },
    {
        "name": "Dayforce Data Conversion Support",
        "service_line": "HR Strategy and Operations",
        "description": "Dayforce HCM data conversion and migration support for HR transformation.",
        "start_date": "2024-05-20", "end_date": "2025-08-29", "status": "closed",
        "staff_count": 7,
        "key_staff": [
            {"name": "Dan Staley", "role": "Principal, Engagement Leader", "email": "dan.staley@pwc.com"},
            {"name": "Brett Battles", "role": "Director", "email": "brett.battles@pwc.com"},
            {"name": "Adam Stensland", "role": "Director, Engagement Manager", "email": "adam.g.stensland@pwc.com"},
        ],
    },
    {
        "name": "Magna Project Hercules - Phase 3 Reporting",
        "service_line": "FP&A Tech - Enabling Apps",
        "description": "Phase 3 of financial planning and reporting transformation using enabling applications.",
        "start_date": "2025-02-17", "end_date": "2025-07-02", "status": "closed",
        "staff_count": 4,
        "key_staff": [
            {"name": "Leonardo De Biasi", "role": "Principal, Engagement Leader", "email": "leonardo.debiasi@pwc.com"},
            {"name": "Mikayla Call", "role": "Managing Director, Engagement Manager", "email": "mikayla.m.call@pwc.com"},
            {"name": "Jessie Zhang", "role": "Director", "email": "jessie.zhang@pwc.com"},
        ],
    },
]

all_staff = {}
for eng in engagements:
    for s in eng.get("key_staff", []):
        if s["name"] not in all_staff:
            all_staff[s["name"]] = {"name": s["name"], "role": s["role"], "office": None, "email": s["email"]}

summary = {
    "summary_text": "No GRP in client master. 5 advisory engagements (0 open). 8 senior staff.",
    "grp": None,
    "account_team": [],
    "engagement_staff": list(all_staff.values()),
    "engagements": engagements,
    "total_people_count": len(all_staff),
    "has_grp": False,
    "has_account_team": False,
    "filter": "Advisory LoS only. Entity: 846912 (Magna International Inc.). No GRP in client_master.",
}

markdown = """## Global Relationship Partner

No GRP found in PwC client master for Magna International.

## Advisory Engagements

### Magna - OneStream ESG Planning & Blueprint [CLOSED]
*2026-03-02 -- 2026-05-29 | FP&A Tech - Enabling Apps*
OneStream ESG planning and reporting implementation. Phase 1 blueprint and configuration.
- **Leonardo De Biasi** -- Principal, Engagement Leader leonardo.debiasi@pwc.com
- **Will Chen** -- Director will.chen@pwc.com

### Magna International - SSB Phase 0 Planning [CLOSED]
*2025-12-01 -- 2025-12-31 | Finance Operations - Process Support*
Shared services benchmarking and phase 0 planning for finance operations.
- **Nitin Bansal** -- Director, Engagement Manager bansal.nitin@pwc.com

### GBS Location Tool Support [CLOSED]
*2025-10-22 -- 2025-11-07 | Finance Function Strategy*
Global business services location strategy and tool support for Canadian operations.

### Dayforce Data Conversion Support [CLOSED]
*2024-05-20 -- 2025-08-29 | HR Strategy and Operations*
Dayforce HCM data conversion and migration support for HR transformation.
- **Dan Staley** -- Principal, Engagement Leader dan.staley@pwc.com
- **Brett Battles** -- Director brett.battles@pwc.com
- **Adam Stensland** -- Director, Engagement Manager adam.g.stensland@pwc.com

### Magna Project Hercules - Phase 3 Reporting [CLOSED]
*2025-02-17 -- 2025-07-02 | FP&A Tech - Enabling Apps*
Phase 3 of financial planning and reporting transformation.
- **Leonardo De Biasi** -- Principal, Engagement Leader leonardo.debiasi@pwc.com
- **Mikayla Call** -- Managing Director, Engagement Manager mikayla.m.call@pwc.com
- **Jessie Zhang** -- Director jessie.zhang@pwc.com

Advisory engagements only (audit/tax excluded). Entity: Magna International Inc. (846912)."""

existing = db.query(MCPEnrichment).filter(
    MCPEnrichment.entity_type == "company",
    MCPEnrichment.entity_id == COMPANY_ID,
    MCPEnrichment.mcp_source == "people_engagements",
).first()

now = datetime.utcnow()
if existing:
    existing.response_markdown = markdown
    existing.response_summary = json.dumps(summary)
    existing.fetched_at = now
else:
    db.add(MCPEnrichment(
        id=str(uuid.uuid4()), entity_type="company", entity_id=COMPANY_ID,
        mcp_source="people_engagements",
        query_prompt="PwC advisory engagement history for Magna International",
        response_markdown=markdown, response_summary=json.dumps(summary),
        fetched_at=now, stale_after=now + timedelta(days=30),
    ))
db.commit()
print("Magna: DONE")
print(f"  No GRP in client master")
print(f"  5 advisory engagements (0 open)")
print(f"  {len(all_staff)} senior staff, all with emails")
print(f"  0 Strategy& engagements")
db.close()
