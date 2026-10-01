import sqlite3, json
conn = sqlite3.connect("data/signals.db")
c = conn.cursor()
c.execute("SELECT c.name, c.industry FROM companies c ORDER BY c.industry, c.name")
for name, industry in c.fetchall():
    c.execute("SELECT response_summary FROM mcp_enrichments WHERE entity_id = (SELECT id FROM companies WHERE name = ?) AND mcp_source = ?", (name, "people_engagements"))
    row = c.fetchone()
    if not row or not row[0]:
        print(f"  [NONE] {name}")
        continue
    data = json.loads(row[0])
    eng = len(data.get("engagements", []))
    staff = data.get("engagement_staff", [])
    staff_email = sum(1 for s in staff if isinstance(s, dict) and s.get("email"))
    grp = data.get("grp")
    grp_name = grp.get("name", "?") if isinstance(grp, dict) else "none"
    grp_email = "Y" if isinstance(grp, dict) and grp.get("email") else "N"
    issues = 0
    for e in data.get("engagements", []):
        for s in e.get("key_staff", []):
            if isinstance(s, str):
                issues += 1
            elif isinstance(s, dict) and not s.get("email"):
                issues += 1
    tag = "OK" if issues == 0 else f"{issues}!"
    print(f"  [{tag}] {name} | GRP: {grp_name} (e:{grp_email}) | {eng} eng | {staff_email}/{len(staff)} emails")
conn.close()
