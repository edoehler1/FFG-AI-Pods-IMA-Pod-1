import sqlite3, json

conn = sqlite3.connect("data/signals.db")
c = conn.cursor()

c.execute("SELECT c.name, c.industry FROM companies c ORDER BY c.industry, c.name")
companies = c.fetchall()

total_ok = 0
issues = []

for name, industry in companies:
    c.execute(
        "SELECT response_summary FROM mcp_enrichments WHERE entity_id = (SELECT id FROM companies WHERE name = ?) AND mcp_source = ?",
        (name, "people_engagements"),
    )
    row = c.fetchone()
    if not row or not row[0]:
        issues.append(f"{name}: NO DATA")
        continue

    data = json.loads(row[0])
    eng_count = len(data.get("engagements", []))

    # Check for audit leaks
    for eng in data.get("engagements", []):
        sl = (eng.get("service_line") or "").lower()
        n = (eng.get("name") or "").lower()
        if "integrated audit" in sl or "integrated audit" in n or "gaas" in sl or "attestation" in sl:
            issues.append(f"{name}: AUDIT LEAK - {eng.get('name', '?')}")

    # Check emails on key_staff
    for eng in data.get("engagements", []):
        for s in eng.get("key_staff", []):
            if isinstance(s, dict) and not s.get("email"):
                issues.append(f"{name}: MISSING EMAIL - {s.get('name', '?')}")
            elif isinstance(s, str):
                issues.append(f"{name}: OLD FORMAT (string) - {s}")

    # Check GRP email
    grp = data.get("grp")
    if grp and isinstance(grp, dict) and not grp.get("email"):
        issues.append(f"{name}: GRP MISSING EMAIL - {grp.get('name', '?')}")

    total_ok += 1

print(f"Companies with data: {total_ok}/{len(companies)}")
print()
if issues:
    print(f"Issues ({len(issues)}):")
    for i in issues:
        print(f"  {i}")
else:
    print("No issues!")
conn.close()
