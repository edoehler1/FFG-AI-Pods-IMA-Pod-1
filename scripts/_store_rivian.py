import json, sys, os, uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.mcp_enrichment import MCPEnrichment

engine = create_engine("sqlite:///data/signals.db", connect_args={"check_same_thread": False})
db = sessionmaker(bind=engine)()

COMPANY_ID = "0a8c1083-8382-4ab7-be68-a775ead514fd"

engagements = [
    {
        "name": "AI-Driven Automation - V3",
        "service_line": None,
        "description": "AI-driven automation initiative for Rivian's operations. Technology advisory engagement.",
        "start_date": "2026-04-27", "end_date": "2026-06-18", "status": "closed",
        "staff_count": 5,
        "key_staff": [
            {"name": "Soumya Sen", "role": "Director", "email": "soumya.a.sen@pwc.com"},
            {"name": "Rian Oosthuizen", "role": "Director, Commercial & Service Excellence", "email": "rian.oosthuizen@pwc.com"},
        ],
    },
    {
        "name": "Rivian IP and Workforce Valuation",
        "service_line": "Vals - Tax Valuation",
        "description": "Intellectual property and workforce valuation for tax purposes.",
        "start_date": "2025-05-15", "end_date": "2025-08-31", "status": "closed",
        "staff_count": 3,
        "key_staff": [
            {"name": "Chad Morrissey", "role": "Principal, Engagement Leader", "email": "chad.morrissey@pwc.com"},
        ],
    },
    {
        "name": "Rivian Automotive Priority PD",
        "service_line": None,
        "description": "Cross-LoS priority pursuit and deal development for Rivian across advisory service lines.",
        "start_date": "2023-07-11", "end_date": "2025-06-27", "status": "closed",
        "staff_count": 20,
        "key_staff": [
            {"name": "Mark Bellantoni", "role": "Partner, CMAAS/Deals", "email": "mark.bellantoni@pwc.com"},
            {"name": "Clifford Eng", "role": "Partner", "email": "clifford.eng@pwc.com"},
            {"name": "Todd Martin", "role": "Principal", "email": "todd.martin@pwc.com"},
            {"name": "Debra Skorupka", "role": "Principal", "email": "debra.skorupka@pwc.com"},
            {"name": "Brad Goehle", "role": "Principal", "email": "brad.goehle@pwc.com"},
            {"name": "Ravi Krovidi", "role": "Managing Director", "email": "ravi.krovidi@pwc.com"},
            {"name": "Sara Frank", "role": "Managing Director", "email": "sara.frank@pwc.com"},
            {"name": "Anthony Sabatino", "role": "Director", "email": "anthony.sabatino@pwc.com"},
            {"name": "Amarnath Putta", "role": "Director", "email": "amarnath.putta@pwc.com"},
            {"name": "Shreerang Mhashelkar", "role": "Director", "email": "shreerang.mhashelkar@pwc.com"},
            {"name": "Teddy Fragopoulos", "role": "Director", "email": "teddy.s.fragopoulos@pwc.com"},
            {"name": "Sameer Bhoyar", "role": "Director", "email": "sameer.bhoyar@pwc.com"},
            {"name": "Harish Upputuri", "role": "Director", "email": "harish.upputuri@pwc.com"},
            {"name": "Angela Moore", "role": "Director", "email": "angela.moore@pwc.com"},
        ],
    },
]

all_staff = {}
for eng in engagements:
    for s in eng.get("key_staff", []):
        if s["name"] not in all_staff:
            all_staff[s["name"]] = {"name": s["name"], "role": s["role"], "office": None, "email": s["email"]}

summary = {
    "summary_text": "GRP: C.J. Finn (Partner). 3 advisory engagements (0 open). 17 senior staff.",
    "grp": {"name": "C.J. Finn", "role": "Partner", "office": None, "email": "charles.j.finn@pwc.com"},
    "account_team": [],
    "engagement_staff": list(all_staff.values()),
    "engagements": engagements,
    "total_people_count": len(all_staff),
    "has_grp": True,
    "has_account_team": False,
    "filter": "Advisory LoS only. Entities: 107697027 (Rivian Automotive Inc.), 117806521 (Rivian Automotive LLC) — umbrella search.",
}

markdown = """## Global Relationship Partner

**C.J. Finn** -- Partner (charles.j.finn@pwc.com)

## Advisory Engagements

### AI-Driven Automation - V3 [CLOSED]
*2026-04-27 -- 2026-06-18*
AI-driven automation initiative for Rivian's operations.
- **Soumya Sen** -- Director soumya.a.sen@pwc.com
- **Rian Oosthuizen** -- Director, Commercial & Service Excellence rian.oosthuizen@pwc.com

### Rivian IP and Workforce Valuation [CLOSED]
*2025-05-15 -- 2025-08-31 | Service: Vals - Tax Valuation*
IP and workforce valuation for tax purposes.
- **Chad Morrissey** -- Principal, Engagement Leader chad.morrissey@pwc.com

### Rivian Automotive Priority PD [CLOSED]
*2023-07-11 -- 2025-06-27*
Cross-LoS priority pursuit and deal development across advisory service lines.
- **Mark Bellantoni** -- Partner, CMAAS/Deals mark.bellantoni@pwc.com
- **Clifford Eng** -- Partner clifford.eng@pwc.com
- **Todd Martin** -- Principal todd.martin@pwc.com
- **Debra Skorupka** -- Principal debra.skorupka@pwc.com
- **Brad Goehle** -- Principal brad.goehle@pwc.com
- **Ravi Krovidi** -- Managing Director ravi.krovidi@pwc.com
- **Sara Frank** -- Managing Director sara.frank@pwc.com
- **Anthony Sabatino** -- Director anthony.sabatino@pwc.com
- **Amarnath Putta** -- Director amarnath.putta@pwc.com
- **Shreerang Mhashelkar** -- Director shreerang.mhashelkar@pwc.com
- **Teddy Fragopoulos** -- Director teddy.s.fragopoulos@pwc.com
- **Sameer Bhoyar** -- Director sameer.bhoyar@pwc.com
- **Harish Upputuri** -- Director harish.upputuri@pwc.com
- **Angela Moore** -- Director angela.moore@pwc.com

Rivian is a US Top Account and Focus 500. Advisory engagements only (audit/tax excluded)."""

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
        query_prompt="PwC advisory engagement history for Rivian Automotive",
        response_markdown=markdown, response_summary=json.dumps(summary),
        fetched_at=now, stale_after=now + timedelta(days=30),
    ))
db.commit()
print("Rivian: DONE")
print(f"  GRP: C.J. Finn (charles.j.finn@pwc.com)")
print(f"  3 advisory engagements (0 open)")
print(f"  {len(all_staff)} senior staff, all with emails")
print(f"  0 Strategy& engagements")
db.close()
