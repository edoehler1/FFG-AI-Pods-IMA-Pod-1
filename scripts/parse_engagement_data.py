"""
Reusable parser for People Connector engagement data.
Converts raw MCP JSON into the Aptiv-format structured summary.

Format rules (per Gabriel):
- Engagements listed by engagement, chronological (newest first)
- Only Principals/Directors shown per engagement (with emails where available)
- Brief description of what the engagement is
- Open/Closed status with dates
- NO account team member dump
- NO generic staff lists
- GRP only in Key Relationships
"""

import json
from datetime import datetime


SENIOR_ROLES = {"Partner", "Principal", "Director", "Managing Director"}


def parse_engagement_file(filepath: str) -> dict:
    with open(filepath) as f:
        data = json.load(f)
    return parse_engagement_data(data)


def parse_engagement_data(data: dict) -> dict:
    """Parse raw MCP engagement_client_finder response into Aptiv-format summary."""

    # Extract GRP from client_master
    grp = None
    client_masters = data.get("facets", {}).get("client_master", [])
    for cm in client_masters:
        grp_name = cm.get("global_relationship_partner_name")
        if grp_name:
            grp = {"name": grp_name, "role": "Partner", "office": None, "email": None}
            break

    # Parse engagements
    engagements = []
    all_senior_staff = {}  # dedupe by name

    for eng in data.get("engagements", []):
        eng_name = eng.get("engagement_name", "unnamed")
        start = eng.get("engagement_start_date") or eng.get("activity_start")
        end = eng.get("engagement_end_date") or eng.get("activity_end")

        # Determine status
        status = "open"
        if end:
            try:
                end_date = datetime.strptime(end, "%Y-%m-%d")
                if end_date < datetime.utcnow():
                    status = "closed"
            except ValueError:
                pass

        # Collect service lines and staff from projects
        service_lines = set()
        staff_list = []
        total_staff = 0

        for proj in eng.get("projects", []):
            sl = proj.get("service_line")
            if sl:
                service_lines.add(sl)

            for person in proj.get("staff", []):
                total_staff += 1
                title = person.get("business_title") or person.get("role") or ""
                role = person.get("role") or ""
                formal = person.get("formal_role") or ""
                name = person.get("display_name") or ""

                if not name:
                    continue

                # Only keep Principals/Directors
                is_senior = False
                for sr in SENIOR_ROLES:
                    if sr.lower() in title.lower() or sr.lower() in role.lower():
                        is_senior = True
                        break

                if is_senior:
                    role_label = title
                    if formal:
                        role_label = f"{title}, {formal}"

                    staff_entry = {
                        "name": name,
                        "role": role_label,
                        "email": None,  # filled by email lookups later
                    }
                    staff_list.append(staff_entry)

                    if name not in all_senior_staff:
                        all_senior_staff[name] = {
                            "name": name,
                            "role": title,
                            "office": None,
                            "email": None,
                        }

        # Dedupe staff within this engagement
        seen_names = set()
        deduped_staff = []
        for s in staff_list:
            if s["name"] not in seen_names:
                seen_names.add(s["name"])
                deduped_staff.append(s)

        service_line = ", ".join(sorted(service_lines)) if service_lines else None

        # Infer description from name + service line
        description = _infer_description(eng_name, service_line)

        engagements.append({
            "name": eng_name,
            "service_line": service_line,
            "description": description,
            "start_date": start,
            "end_date": end,
            "status": status,
            "staff_count": total_staff,
            "key_staff": deduped_staff,
        })

    # Sort newest first
    engagements.sort(key=lambda e: e.get("start_date") or "0000", reverse=True)

    # Build summary
    open_count = sum(1 for e in engagements if e["status"] == "open")
    strategy_count = sum(1 for e in engagements if _is_strategy(e))

    summary_parts = []
    if grp:
        summary_parts.append(f"GRP: {grp['name']}")
    summary_parts.append(f"{len(engagements)} engagements ({open_count} open)")
    if strategy_count:
        summary_parts.append(f"{strategy_count} Strategy&")

    return {
        "summary_text": ". ".join(summary_parts) + ".",
        "grp": grp,
        "account_team": [],  # intentionally empty — not shown per Gabriel's request
        "engagement_staff": list(all_senior_staff.values()),
        "engagements": engagements,
        "total_people_count": len(all_senior_staff),
        "has_grp": grp is not None,
        "has_account_team": False,
    }


def apply_email_lookups(summary: dict, email_map: dict[str, str]):
    """Apply email lookups to the structured summary. email_map is {name: email}."""
    if summary.get("grp") and summary["grp"]["name"] in email_map:
        summary["grp"]["email"] = email_map[summary["grp"]["name"]]

    for staff in summary.get("engagement_staff", []):
        if staff["name"] in email_map:
            staff["email"] = email_map[staff["name"]]

    for eng in summary.get("engagements", []):
        for staff in eng.get("key_staff", []):
            if staff["name"] in email_map:
                staff["email"] = email_map[staff["name"]]


def build_markdown(summary: dict, company_name: str) -> str:
    """Build readable markdown from structured summary."""
    lines = []

    if summary.get("grp"):
        g = summary["grp"]
        lines.append("## Global Relationship Partner")
        lines.append("")
        email_str = f" ({g['email']})" if g.get("email") else ""
        office_str = f", {g['office']}" if g.get("office") else ""
        lines.append(f"**{g['name']}** -- {g.get('role', 'Partner')}{office_str}{email_str}")
        lines.append("")

    # Split into strategy and other
    strategy_engs = [e for e in summary.get("engagements", []) if _is_strategy(e)]
    other_engs = [e for e in summary.get("engagements", []) if not _is_strategy(e)]

    if strategy_engs:
        lines.append("## Strategy& Engagements")
        lines.append("")
        for eng in strategy_engs:
            lines.extend(_format_engagement_md(eng))
            lines.append("")

    if other_engs:
        lines.append("## Other Advisory Engagements")
        lines.append("")
        for eng in other_engs:
            lines.extend(_format_engagement_md(eng))
            lines.append("")

    return "\n".join(lines)


def _format_engagement_md(eng: dict) -> list[str]:
    lines = []
    status_label = "OPEN" if eng["status"] == "open" else "CLOSED"
    lines.append(f"### {eng['name']} [{status_label}]")

    dates = [eng.get("start_date"), eng.get("end_date")]
    date_str = " -- ".join(d for d in dates if d)
    parts = []
    if date_str:
        parts.append(f"*{date_str}*")
    if eng.get("service_line"):
        parts.append(f"Service: {eng['service_line']}")
    if parts:
        lines.append(" | ".join(parts))

    if eng.get("description"):
        lines.append(eng["description"])

    for s in eng.get("key_staff", []):
        email_str = f" {s['email']}" if s.get("email") else ""
        lines.append(f"- **{s['name']}** -- {s.get('role', '')}{email_str}")

    return lines


def _is_strategy(eng: dict) -> bool:
    name = (eng.get("name") or "").lower()
    sl = (eng.get("service_line") or "").lower()
    keywords = ["strategy", "consulting solutions", "cost structure", "value realiz",
                "manufacturing strategy", "operations strategy", "transformation"]
    for kw in keywords:
        if kw in name or kw in sl:
            return True
    return False


def _infer_description(name: str, service_line: str | None) -> str:
    """Infer a brief description from engagement name and service line."""
    if not name:
        return service_line or ""
    # Clean up common prefixes
    clean = name
    for prefix in ["DNU ", "D_N_U ", "REMOVE ", "DNU_", "D_N_U_"]:
        if clean.upper().startswith(prefix):
            clean = clean[len(prefix):]

    sl = service_line or ""

    # Common patterns
    if "audit" in clean.lower() and "defense" in clean.lower():
        return f"Audit defense support. {sl}." if sl else "Audit defense support."
    if "divestiture" in clean.lower() or "separation" in clean.lower():
        return f"Divestiture and separation advisory. {sl}." if sl else "Divestiture and separation advisory."
    if "nist" in clean.lower() or "csf" in clean.lower():
        return f"Cybersecurity framework assessment. {sl}." if sl else "Cybersecurity framework assessment."
    if "sox" in clean.lower():
        return f"SOX compliance and managed services. {sl}." if sl else "SOX compliance managed services."
    if "valuation" in clean.lower() or "vals" in clean.lower():
        return f"Valuation services. {sl}." if sl else "Valuation advisory."
    if "erp" in clean.lower() or "sap" in clean.lower() or "workday" in clean.lower():
        return f"Enterprise systems implementation. {sl}." if sl else "Enterprise systems implementation."
    if "tax" in clean.lower() or "sut" in clean.lower() or "salt" in clean.lower():
        return f"Tax advisory and compliance. {sl}." if sl else "Tax advisory and compliance."
    if "restructur" in clean.lower():
        return f"Restructuring advisory. {sl}." if sl else "Restructuring advisory."
    if "sustainability" in clean.lower() or "esg" in clean.lower():
        return f"Sustainability and ESG advisory. {sl}." if sl else "Sustainability and ESG advisory."
    if "manufacturing" in clean.lower() and "strategy" in clean.lower():
        return f"Manufacturing strategy and operational footprint optimization."
    if "strategy" in clean.lower():
        return f"Strategy advisory. {sl}." if sl else "Strategy advisory."
    if "cyber" in clean.lower():
        return f"Cybersecurity advisory. {sl}." if sl else "Cybersecurity advisory."

    # Fallback: just use service line if available
    if sl:
        return f"{sl}."
    return ""
