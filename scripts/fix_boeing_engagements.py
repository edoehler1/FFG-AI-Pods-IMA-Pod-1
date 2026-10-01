"""Fix Boeing enrichment: add engagements array for the Relationships tab."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import SessionLocal
from app.models.mcp_enrichment import MCPEnrichment

db = SessionLocal()
boeing_id = "8a4a4f33-6ec5-4736-934d-606f86f74076"
e = db.query(MCPEnrichment).filter(
    MCPEnrichment.entity_id == boeing_id,
    MCPEnrichment.mcp_source == "people_engagements",
).first()

summary = json.loads(e.response_summary)

summary["engagements"] = [
    {
        "name": "AI Governance & Strategy Support",
        "service_line": "Strategy Advisory",
        "description": "AI governance framework design and enterprise AI strategy for Boeing technology leadership.",
        "start_date": "2026-08-03",
        "end_date": "2026-09-29",
        "status": "closed",
        "staff_count": 9,
        "key_staff": [
            {"name": "Vikram Latawa", "role": "Partner", "email": "vikram.latawa@pwc.com"},
            {"name": "Rajesh Patnaik", "role": "Partner", "email": "rajesh.patnaik@pwc.com"},
            {"name": "Harshul Joshi", "role": "Partner", "email": "harshul.joshi@pwc.com"},
            {"name": "Kristen Gaudio", "role": "Director", "email": "kristen.n.gaudio@pwc.com"},
            {"name": "Ed Golden", "role": "Director", "email": "edward.golden@pwc.com"},
            {"name": "Luisa Bramao Ramos", "role": "Director", "email": "luisa.m.bramao.ramos@pwc.com"},
            {"name": "Brad Benson", "role": "Director", "email": "bradley.benson@pwc.com"},
        ],
    },
    {
        "name": "Software Selection and Vendor Management",
        "service_line": "Advisory",
        "description": "Enterprise software rationalization and vendor strategy.",
        "start_date": "2026-08-03",
        "end_date": "2026-09-29",
        "status": "open",
        "staff_count": 0,
        "key_staff": [],
    },
    {
        "name": "BDA Workday HCM Phase 1",
        "service_line": "Workforce Tech - Workday HCM",
        "description": "Enterprise HCM implementation.",
        "start_date": "2026-07-27",
        "end_date": "2026-09-29",
        "status": "open",
        "staff_count": 1,
        "key_staff": [{"name": "Alexx Baum", "role": "Director", "email": "alexandra.k.baum@pwc.com"}],
    },
    {
        "name": "Boeing ZT Cyber PMO - Extension",
        "service_line": "Cyber Enterprise and Cloud Security",
        "description": "Zero Trust cybersecurity program management.",
        "start_date": "2026-07-27",
        "end_date": "2026-09-28",
        "status": "closed",
        "staff_count": 2,
        "key_staff": [
            {"name": "Chad Gray", "role": "Principal", "email": "chad.gray@pwc.com"},
            {"name": "Bridget Mott", "role": "Senior Manager", "email": "bridget.uhle@pwc.com"},
        ],
    },
    {
        "name": "App Wedge Phase 3 Support",
        "service_line": "Other Advisory",
        "description": "Enterprise application modernization.",
        "start_date": "2026-04-06",
        "end_date": "2026-09-28",
        "status": "closed",
        "staff_count": 3,
        "key_staff": [
            {"name": "Chad Gray", "role": "Principal", "email": "chad.gray@pwc.com"},
            {"name": "Anbu Samuel", "role": "Director", "email": "anbu.s.samuel@pwc.com"},
            {"name": "Andrew Schiefelbein", "role": "Director", "email": "andrew.m.schiefelbein@pwc.com"},
        ],
    },
    {
        "name": "Mgd Svcs - App Evolution Svcs Workday",
        "service_line": "Managed Services",
        "description": "Ongoing Workday platform management.",
        "start_date": "2026-03-25",
        "end_date": "2026-09-29",
        "status": "open",
        "staff_count": 1,
        "key_staff": [{"name": "Julie Trent", "role": "Managing Director", "email": "julie.trent@pwc.com"}],
    },
    {
        "name": "Data Mod - Databricks",
        "service_line": "Other Advisory",
        "description": "Large-scale data architecture and engineering program.",
        "start_date": "2026-03-12",
        "end_date": "2026-09-29",
        "status": "open",
        "staff_count": 13,
        "key_staff": [
            {"name": "Anbu Mani", "role": "Principal", "email": "anbu.mani@pwc.com"},
            {"name": "Tanya Khaiyanun", "role": "Principal", "email": "tanya.khaiyanun@pwc.com"},
            {"name": "Shane Kondo", "role": "Principal", "email": "shane.kondo@pwc.com"},
            {"name": "Sambaran Chakravorty", "role": "Director", "email": "sambaran.chakravorty@pwc.com"},
        ],
    },
    {
        "name": "DD Invoice Testing",
        "service_line": "Investigation and Forensics",
        "description": "Investigation and Forensics engagement.",
        "start_date": "2026-02-27",
        "end_date": "2026-12-31",
        "status": "open",
        "staff_count": 2,
        "key_staff": [
            {"name": "Melissa Cefalu", "role": "Partner, Engagement Leader", "email": "melissa.cefalu@pwc.com"},
            {"name": "Daniel Chomat", "role": "Director, Engagement Manager", "email": "daniel.r.chomat@pwc.com"},
        ],
    },
    {
        "name": "Boeing Spirit EM Support",
        "service_line": "Workforce Tech - Workday HCM",
        "description": "Spirit AeroSystems workforce integration support post-acquisition.",
        "start_date": "2026-02-02",
        "end_date": "2026-12-31",
        "status": "open",
        "staff_count": 2,
        "key_staff": [
            {"name": "Danielle White", "role": "Principal, Engagement Leader", "email": "danielle.white@pwc.com"},
            {"name": "Alexx Baum", "role": "Director, Engagement Manager", "email": "alexandra.k.baum@pwc.com"},
        ],
    },
    {
        "name": "2026 Sentinel PMO Support",
        "service_line": "Cyber Enterprise and Cloud Security",
        "description": "Cybersecurity PMO for the Sentinel ICBM program.",
        "start_date": "2026-01-05",
        "end_date": "2027-01-03",
        "status": "open",
        "staff_count": 4,
        "key_staff": [
            {"name": "Chad Gray", "role": "Principal, Engagement Leader", "email": "chad.gray@pwc.com"},
            {"name": "Rich Kneeley", "role": "Managing Director", "email": "richard.j.kneeley@pwc.com"},
            {"name": "Harshul Joshi", "role": "Principal", "email": "harshul.joshi@pwc.com"},
            {"name": "Brad Benson", "role": "Director", "email": "bradley.benson@pwc.com"},
        ],
    },
]

e.response_summary = json.dumps(summary)
db.commit()
print(f"Updated Boeing with {len(summary['engagements'])} engagements")
db.close()
