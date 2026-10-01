"""Fix format issues: remove non-senior staff from key_staff, add missing descriptions."""
import sqlite3
import json

NON_SENIOR_PATTERNS = ["senior manager", "senior associate"]

def is_non_senior(role: str) -> bool:
    role_lower = role.lower().strip()
    for p in NON_SENIOR_PATTERNS:
        if p in role_lower:
            return True
    if role_lower == "manager":
        return True
    if role_lower == "associate":
        return True
    return False

def infer_description(name: str, service_line: str | None) -> str:
    if not name:
        return service_line or ""
    n = name.lower()
    sl = (service_line or "").lower()
    if "sox" in n: return "SOX compliance and internal audit managed services."
    if "data mod" in n or "databricks" in n: return "Data modernization and analytics platform implementation."
    if "app wedge" in n: return "Application security assessment and process design."
    if "pmo" in n or "program" in n and "oversight" in n: return "Program management office support."
    if "licensing" in n: return "Software licensing management and compliance."
    if "forensic" in n or "investigation" in n: return "Forensic accounting and investigation support."
    if "fp&a" in n or "oracle epm" in n: return "Financial planning and analysis technology implementation."
    if "privacy" in n or "data governance" in n: return "Privacy and data governance program build."
    if "sailpoint" in n or "iam" in n: return "Identity and access management implementation."
    if "treasury" in n or "tms" in n: return "Treasury management system implementation."
    if "cmaas" in n: return "Capital markets and accounting advisory services."
    if "finance" in n and "operation" in n: return "Finance operations transformation and support."
    if "gis" in n or "nextgen" in n: return "Next-generation GIS platform implementation."
    if "pqc" in n: return "Post-quantum cryptography readiness planning."
    if "wind farm" in n or "repower" in n: return "Wind farm repower tax valuation services."
    if "pwa" in n: return "Prevailing wage and apprenticeship compliance."
    if "maximo" in n or "atlas" in n: return "Maximo asset management implementation."
    if "salesforce" in n or "crm" in n: return "Salesforce CRM implementation and support."
    if "etrm" in n or "aurora" in n: return "Energy trading and risk management system controls."
    if "abac" in n or "tprm" in n: return "Anti-bribery/corruption and third-party risk management."
    if "dd invoice" in n: return "Due diligence invoice testing and forensic review."
    if "sentinel" in n: return "Cybersecurity sentinel program management."
    if "vendor" in n and "select" in n: return "Software selection and vendor management advisory."
    if sl: return f"{sl}."
    return ""

conn = sqlite3.connect("data/signals.db")
c = conn.cursor()

fixed = 0
removed_staff = 0
added_desc = 0

c.execute("SELECT c.name, e.entity_id FROM companies c JOIN mcp_enrichments e ON c.id = e.entity_id AND e.mcp_source = 'people_engagements' ORDER BY c.name")
rows = c.fetchall()

for company_name, entity_id in rows:
    c.execute("SELECT response_summary FROM mcp_enrichments WHERE entity_id = ? AND mcp_source = 'people_engagements'", (entity_id,))
    row = c.fetchone()
    if not row or not row[0]: continue
    data = json.loads(row[0])
    changed = False

    for eng in data.get("engagements", []):
        orig = len(eng.get("key_staff", []))
        eng["key_staff"] = [s for s in eng.get("key_staff", []) if not isinstance(s, dict) or not is_non_senior(s.get("role", ""))]
        rm = orig - len(eng["key_staff"])
        if rm > 0:
            removed_staff += rm
            changed = True
        if not eng.get("description"):
            desc = infer_description(eng.get("name", ""), eng.get("service_line"))
            if desc:
                eng["description"] = desc
                added_desc += 1
                changed = True

    if data.get("engagement_staff"):
        orig = len(data["engagement_staff"])
        data["engagement_staff"] = [s for s in data["engagement_staff"] if not isinstance(s, dict) or not is_non_senior(s.get("role", ""))]
        removed_staff += orig - len(data["engagement_staff"])

    if changed:
        c.execute("UPDATE mcp_enrichments SET response_summary = ? WHERE entity_id = ? AND mcp_source = 'people_engagements'", (json.dumps(data), entity_id))
        fixed += 1

conn.commit()

# Update seed fixture
c.execute("SELECT c.name, e.response_summary, e.response_markdown, e.query_prompt FROM mcp_enrichments e JOIN companies c ON c.id = e.entity_id WHERE e.mcp_source = 'people_engagements' ORDER BY c.name")
records = [{"company_name": n, "entity_type": "company", "mcp_source": "people_engagements", "query_prompt": p or "", "response_markdown": m or "", "response_summary": json.loads(s) if s else None} for n, s, m, p in c.fetchall()]
with open("backend/seed_data/people_connector_enrichments.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"Fixed {fixed} companies: removed {removed_staff} non-senior, added {added_desc} descriptions")

# Verify
issues = 0
for _, eid in rows:
    c.execute("SELECT response_summary FROM mcp_enrichments WHERE entity_id = ? AND mcp_source = 'people_engagements'", (eid,))
    r = c.fetchone()
    if not r or not r[0]: continue
    d = json.loads(r[0])
    for eng in d.get("engagements", []):
        if not eng.get("description"): issues += 1
        for s in eng.get("key_staff", []):
            if isinstance(s, dict) and is_non_senior(s.get("role", "")): issues += 1
print(f"Remaining issues: {issues}")
conn.close()
