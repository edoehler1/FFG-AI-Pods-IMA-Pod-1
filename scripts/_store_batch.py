import sys, json, uuid
from datetime import datetime, timedelta
sys.path.insert(0, "backend")
from parse_engagement_data import build_markdown
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.mcp_enrichment import MCPEnrichment
import sqlite3

engine = create_engine("sqlite:///data/signals.db", connect_args={"check_same_thread": False})
db = sessionmaker(bind=engine)()
conn = sqlite3.connect("data/signals.db")
c = conn.cursor()
now = datetime.utcnow()

def store(company_name, data):
    c.execute("SELECT id FROM companies WHERE name = ?", (company_name,))
    row = c.fetchone()
    if not row:
        print(f"  NOT FOUND: {company_name}")
        return
    cid = row[0]
    md = build_markdown(data, company_name)
    ex = db.query(MCPEnrichment).filter(MCPEnrichment.entity_type == "company", MCPEnrichment.entity_id == cid, MCPEnrichment.mcp_source == "people_engagements").first()
    if ex:
        ex.response_markdown = md
        ex.response_summary = json.dumps(data)
        ex.fetched_at = now
    else:
        db.add(MCPEnrichment(id=str(uuid.uuid4()), entity_type="company", entity_id=cid, mcp_source="people_engagements", query_prompt=f"PwC advisory for {company_name}", response_markdown=md, response_summary=json.dumps(data), fetched_at=now, stale_after=now+timedelta(days=30)))
    db.commit()
    open_ct = sum(1 for e in data.get("engagements", []) if e.get("status") == "open")
    print(f"  {company_name}: {len(data.get('engagements', []))} engs ({open_ct} open)")

# Tesla
store("Tesla Inc", {
    "summary_text": "GRP: Robert W Conklin. 1 advisory engagement. 2 senior staff.",
    "grp": {"name": "Robert W Conklin", "role": "Partner", "office": None, "email": "robert.conklin@pwc.com"},
    "account_team": [],
    "engagement_staff": [{"name": "Grant Peterson", "role": "Director", "office": None, "email": "grant.peterson@pwc.com"}],
    "engagements": [{"name": "Tesla Workforce Solutions FY25", "service_line": "Workforce Solutions", "description": "Workforce strategy and solutions for Tesla operations.", "start_date": "2025-10-06", "end_date": "2025-12-01", "status": "closed", "staff_count": 3, "key_staff": [{"name": "Grant Peterson", "role": "Director", "email": "grant.peterson@pwc.com"}]}],
    "total_people_count": 2, "has_grp": True, "has_account_team": False,
    "filter": "Advisory LoS only. Tesla audit excluded. Entity 816894.",
})

# Stellantis
store("Stellantis", {
    "summary_text": "GRP: Marc Gerretsen (non-US). 0 advisory engagements.",
    "grp": {"name": "Marc Gerretsen", "role": "Partner (non-US)", "office": None, "email": None},
    "account_team": [], "engagement_staff": [], "engagements": [],
    "total_people_count": 0, "has_grp": True, "has_account_team": False,
    "filter": "Advisory LoS only. Stellantis NV (118422325) - 0 advisory engagements.",
})

# Magna
store("Magna International", {
    "summary_text": "7 advisory engagements (0 open). 8 senior staff.",
    "grp": None, "has_grp": False, "account_team": [],
    "engagement_staff": [
        {"name": "Leonardo De Biasi", "role": "Principal", "office": None, "email": "leonardo.debiasi@pwc.com"},
        {"name": "Dan Staley", "role": "Principal", "office": None, "email": "dan.staley@pwc.com"},
        {"name": "Mikayla Call", "role": "Managing Director", "office": None, "email": "mikayla.m.call@pwc.com"},
        {"name": "Will Chen", "role": "Director", "office": None, "email": "will.chen@pwc.com"},
        {"name": "Nitin Bansal", "role": "Director", "office": None, "email": "bansal.nitin@pwc.com"},
        {"name": "Brett Battles", "role": "Director", "office": None, "email": "brett.battles@pwc.com"},
        {"name": "Adam Stensland", "role": "Director", "office": None, "email": "adam.g.stensland@pwc.com"},
        {"name": "Jessie Zhang", "role": "Director", "office": None, "email": "jessie.zhang@pwc.com"},
    ],
    "engagements": [
        {"name": "Magna - OneStream ESG Planning & Blueprint", "service_line": "FP&A Tech - Enabling Apps", "description": "OneStream implementation for ESG planning and reporting.", "start_date": "2026-03-02", "end_date": "2026-05-29", "status": "closed", "staff_count": 5, "key_staff": [{"name": "Leonardo De Biasi", "role": "Principal, Engagement Leader", "email": "leonardo.debiasi@pwc.com"}, {"name": "Will Chen", "role": "Director", "email": "will.chen@pwc.com"}]},
        {"name": "Magna Project Hercules Phase 3 Reporting", "service_line": "FP&A Tech - Enabling Apps", "description": "Financial reporting system implementation, Phase 3.", "start_date": "2025-02-17", "end_date": "2025-07-02", "status": "closed", "staff_count": 4, "key_staff": [{"name": "Leonardo De Biasi", "role": "Principal, Engagement Leader", "email": "leonardo.debiasi@pwc.com"}, {"name": "Mikayla Call", "role": "Managing Director, Engagement Manager", "email": "mikayla.m.call@pwc.com"}, {"name": "Jessie Zhang", "role": "Director", "email": "jessie.zhang@pwc.com"}]},
        {"name": "Magna SSB Phase 0 Planning", "service_line": "Finance Operations - Process Support", "description": "Shared services and business process support planning.", "start_date": "2025-12-01", "end_date": "2025-12-31", "status": "closed", "staff_count": 1, "key_staff": [{"name": "Nitin Bansal", "role": "Director, Engagement Manager", "email": "bansal.nitin@pwc.com"}]},
        {"name": "Dayforce Data Conversion Support", "service_line": "HR Strategy and Operations", "description": "HR system data migration for Dayforce HCM platform.", "start_date": "2024-05-20", "end_date": "2025-08-29", "status": "closed", "staff_count": 7, "key_staff": [{"name": "Dan Staley", "role": "Principal, Engagement Leader", "email": "dan.staley@pwc.com"}, {"name": "Adam Stensland", "role": "Director, Engagement Manager", "email": "adam.g.stensland@pwc.com"}, {"name": "Brett Battles", "role": "Director", "email": "brett.battles@pwc.com"}]},
        {"name": "GBS Location Tool Support", "service_line": "Finance Function Strategy", "description": "Global Business Services location assessment.", "start_date": "2025-10-22", "end_date": "2025-11-07", "status": "closed", "staff_count": 2, "key_staff": []},
    ],
    "total_people_count": 8, "has_account_team": False,
    "filter": "Advisory LoS only. Magna International Inc (846912).",
})

# Rivian (from earlier inline data)
store("Rivian Automotive", {
    "summary_text": "GRP: C.J. Finn. 1 advisory engagement (1 open). 2 senior staff.",
    "grp": {"name": "C.J. Finn", "role": "Partner", "office": None, "email": "charles.j.finn@pwc.com"},
    "account_team": [], "has_grp": True, "has_account_team": False,
    "engagement_staff": [
        {"name": "Soumya Sen", "role": "Director", "office": None, "email": None},
        {"name": "Rian Oosthuizen", "role": "Director", "office": None, "email": None},
    ],
    "engagements": [
        {"name": "AI-Driven Automation - V3", "service_line": None, "description": "AI-driven automation platform for Rivian operations.", "start_date": "2026-04-27", "end_date": "2026-06-18", "status": "closed", "staff_count": 5, "key_staff": [{"name": "Soumya Sen", "role": "Director", "email": None}, {"name": "Rian Oosthuizen", "role": "Director", "email": None}]},
    ],
    "total_people_count": 2,
    "filter": "Advisory LoS only. Rivian umbrella (107697027, 117806521). Most engagement is audit/pursuit.",
})

conn.close()
db.close()
print("Done.")
