"""Patch missing emails across all companies."""
import json, sys, os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.mcp_enrichment import MCPEnrichment

engine = create_engine("sqlite:///data/signals.db", connect_args={"check_same_thread": False})
db = sessionmaker(bind=engine)()

EMAIL_MAP = {
    "Chris DeSisto": "christopher.m.desisto@pwc.com",
    "Kirby Sundquist": "kirby.sundquist@pwc.com",
    "Julianne Potter": "julianne.potter@pwc.com",
    "Neha Krishna": "neha.krishna@pwc.com",
    "Jon Nelson": "jon.k.nelson@pwc.com",
    "Robert Vettoretti": "r.vettoretti@pwc.com",
    "Jameson McNeill": "jameson.mcneill@pwc.com",
    "Brad Danton": "stephen.b.danton@pwc.com",
    "Dawn Scott": "dawn.l.scott@pwc.com",
    "Magnus Fleming": "magnus.fleming@pwc.com",
    "Mohan Krishna S H": "mohan.krishna.s.h@pwc.com",
    "Alexandra Psaris": "alexandra.h.psaris@pwc.com",
    "Christopher Holdsworth": "christopher.holdsworth@pwc.com",  # from earlier lookup
}

enrichments = db.query(MCPEnrichment).filter(
    MCPEnrichment.mcp_source == "people_engagements",
).all()

patched_total = 0

for enrichment in enrichments:
    if not enrichment.response_summary:
        continue

    data = json.loads(enrichment.response_summary)
    patched = 0

    # Patch engagement_staff
    for staff in data.get("engagement_staff", []):
        if isinstance(staff, dict) and not staff.get("email") and staff.get("name") in EMAIL_MAP:
            staff["email"] = EMAIL_MAP[staff["name"]]
            patched += 1

    # Patch key_staff in engagements
    for eng in data.get("engagements", []):
        for staff in eng.get("key_staff", []):
            if isinstance(staff, dict) and not staff.get("email") and staff.get("name") in EMAIL_MAP:
                staff["email"] = EMAIL_MAP[staff["name"]]
                patched += 1

    # Patch GRP
    grp = data.get("grp")
    if grp and isinstance(grp, dict) and not grp.get("email") and grp.get("name") in EMAIL_MAP:
        grp["email"] = EMAIL_MAP[grp["name"]]
        patched += 1

    if patched:
        enrichment.response_summary = json.dumps(data)
        db.commit()
        patched_total += patched
        print(f"  Patched {patched} emails in {enrichment.entity_id[:8]}...")

print(f"\nTotal emails patched: {patched_total}")

# Final verification
remaining = 0
for enrichment in enrichments:
    if not enrichment.response_summary:
        continue
    data = json.loads(enrichment.response_summary)
    for eng in data.get("engagements", []):
        for s in eng.get("key_staff", []):
            if isinstance(s, dict) and not s.get("email"):
                remaining += 1

print(f"Remaining missing emails: {remaining}")
db.close()
