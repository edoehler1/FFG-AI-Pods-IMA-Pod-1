"""Bulk cleanup: remove audit engagements and report missing emails."""
import json, sys, os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.mcp_enrichment import MCPEnrichment
from app.models.company import Company

engine = create_engine("sqlite:///data/signals.db", connect_args={"check_same_thread": False})
db = sessionmaker(bind=engine)()

AUDIT_KEYWORDS = ["audit", "integrated audit", "sec -", "gaas", "attestation", "assurance", "sec-", "aup"]

companies = db.query(Company).order_by(Company.industry, Company.name).all()

for company in companies:
    enrichment = db.query(MCPEnrichment).filter(
        MCPEnrichment.entity_type == "company",
        MCPEnrichment.entity_id == company.id,
        MCPEnrichment.mcp_source == "people_engagements",
    ).first()

    if not enrichment or not enrichment.response_summary:
        continue

    data = json.loads(enrichment.response_summary)
    engs = data.get("engagements", [])
    if not engs:
        continue

    # Remove audit engagements
    clean_engs = []
    removed = []
    for eng in engs:
        sl = (eng.get("service_line") or "").lower()
        nm = (eng.get("name") or "").lower()
        is_audit = any(kw in sl or kw in nm for kw in AUDIT_KEYWORDS)
        if is_audit:
            removed.append(eng.get("name", "unnamed"))
        else:
            clean_engs.append(eng)

    if removed:
        print(f"[{company.name}] Removed {len(removed)} audit engagements:")
        for r in removed:
            print(f"  - {r}")
        data["engagements"] = clean_engs

        # Rebuild engagement_staff from remaining engagements
        remaining_staff = {}
        for eng in clean_engs:
            for s in eng.get("key_staff", []):
                if isinstance(s, dict) and s.get("name") and s["name"] not in remaining_staff:
                    remaining_staff[s["name"]] = s
        data["engagement_staff"] = list(remaining_staff.values())

        enrichment.response_summary = json.dumps(data)
        enrichment.fetched_at = datetime.utcnow()
        db.commit()

    # Report missing emails
    missing = []
    for eng in data.get("engagements", []):
        for s in eng.get("key_staff", []):
            if isinstance(s, dict) and not s.get("email"):
                missing.append(f"{s.get('name', '?')} on {eng.get('name', '?')}")

    if missing:
        print(f"[{company.name}] MISSING EMAILS ({len(missing)}):")
        for m in missing:
            print(f"  - {m}")

db.close()
print("\nCleanup done.")
