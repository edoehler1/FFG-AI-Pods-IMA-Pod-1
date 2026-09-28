"""
People Connector enricher — PwC engagement history per company.

Uses engagement_client_finder to surface who at PwC has worked with a target
company, the GRP, account team members, and recent engagement history.
Feeds into: signal_router.py, outreach_ranker.py, dashboard.py,
weekly_report_agent.py, profile_builder.py, company_analyzer.py.
"""

import json
import re

from ingestion.enrichment.base_enricher import BaseEnricher


class PeopleEngagementEnricher(BaseEnricher):
    mcp_source = "people_engagements"
    entity_type = "company"
    stale_days = 30

    def build_prompts(self, company) -> list[dict]:
        return [
            {
                "label": f"PwC advisory engagement history for {company.name}",
                "prompt": (
                    f"Who at PwC has worked with {company.name} on advisory engagements? "
                    f"Include the Global Relationship Partner (GRP) and account team members. "
                    f"For engagements, filter to Advisory line of service only — "
                    f"exclude Assurance, Tax, and audit work. "
                    f"Show engagement names, dates, and staff with their roles and offices. "
                    f"Use group_by='engagement' and los='Advisory'."
                ),
                "mcp_tool": "engagement_client_finder",
                "mcp_params": {
                    "los": "Advisory",
                    "group_by": "engagement",
                    "time_range": "last_24mo",
                },
            },
        ]

    def store_result(self, db, entity_id, prompt, markdown, summary=None, citations=None):
        parsed = _parse_people(markdown)
        if parsed["has_grp"] or parsed["account_team"] or parsed["engagement_staff"]:
            summary = parsed
        return super().store_result(db, entity_id, prompt, markdown, summary=summary, citations=citations)


def _parse_people(markdown: str) -> dict:
    grp = None
    account_team: list[dict] = []
    engagement_staff: list[dict] = []

    grp = _extract_grp(markdown)
    account_team = _extract_account_team(markdown)
    engagement_staff = _extract_engagement_staff(markdown)

    total = (1 if grp else 0) + len(account_team) + len(engagement_staff)

    parts = []
    if grp:
        grp_desc = f"GRP: {grp['name']}"
        if grp.get("role"):
            grp_desc += f" ({grp['role']}"
            if grp.get("office"):
                grp_desc += f", {grp['office']}"
            grp_desc += ")"
        parts.append(grp_desc)
    if account_team:
        parts.append(f"{len(account_team)} account team member{'s' if len(account_team) != 1 else ''}")
    if engagement_staff:
        parts.append(f"{len(engagement_staff)} engagement staff")

    summary_text = ". ".join(parts) + "." if parts else "No PwC people found."

    return {
        "summary_text": summary_text,
        "grp": grp,
        "account_team": account_team,
        "engagement_staff": engagement_staff,
        "total_people_count": total,
        "has_grp": grp is not None,
        "has_account_team": len(account_team) > 0,
    }


def _extract_grp(markdown: str) -> dict | None:
    patterns = [
        re.compile(
            r"(?:Global\s+Relationship\s+Partner|GRP)\s*[:—–-]\s*\**([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\**",
            re.IGNORECASE,
        ),
        re.compile(
            r"\**([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\**\s*(?:is|serves?\s+as)\s+(?:the\s+)?(?:Global\s+Relationship\s+Partner|GRP)",
            re.IGNORECASE,
        ),
    ]

    for pattern in patterns:
        match = pattern.search(markdown)
        if match:
            name = match.group(1).strip()
            role, office = _extract_role_and_office_near(markdown, match.end(), name)
            return {"name": name, "role": role or "Partner", "office": office}

    return None


def _extract_account_team(markdown: str) -> list[dict]:
    members: list[dict] = []

    section = _get_section(markdown, r"account\s+team")
    if not section:
        return members

    person_pattern = re.compile(
        r"[-•*]\s*\**([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\**"
    )

    for match in person_pattern.finditer(section):
        name = match.group(1).strip()
        role, office = _extract_role_and_office_near(section, match.end(), name)
        members.append({"name": name, "role": role, "office": office})

    return members[:10]


def _extract_engagement_staff(markdown: str) -> list[dict]:
    staff: list[dict] = []

    section_headers = [
        r"engagement\s+(?:staff|team|history)",
        r"(?:people|staff|team)\s+(?:who\s+)?(?:have\s+)?(?:billed|worked|charged)",
        r"recent\s+(?:engagement|project)\s+(?:staff|team)",
    ]

    section = None
    for header in section_headers:
        section = _get_section(markdown, header)
        if section:
            break

    if not section:
        full_people = _extract_all_people(markdown)
        for person in full_people:
            if not any(m["name"] == person["name"] for m in staff):
                staff.append(person)
        return staff[:15]

    person_pattern = re.compile(
        r"[-•*]\s*\**([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\**"
    )

    for match in person_pattern.finditer(section):
        name = match.group(1).strip()
        role, office = _extract_role_and_office_near(section, match.end(), name)
        staff.append({"name": name, "role": role, "office": office})

    return staff[:15]


def _extract_all_people(markdown: str) -> list[dict]:
    """Fallback: extract all person-like entries from the full markdown."""
    people: list[dict] = []
    person_pattern = re.compile(
        r"[-•*]\s*\**([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\**"
    )
    for match in person_pattern.finditer(markdown):
        name = match.group(1).strip()
        if _is_likely_person_name(name):
            role, office = _extract_role_and_office_near(markdown, match.end(), name)
            people.append({"name": name, "role": role, "office": office})
    return people


def _is_likely_person_name(text: str) -> bool:
    skip = {"Global Relationship Partner", "Account Team", "Engagement", "Senior Manager",
            "Managing Director", "Line of Service", "Total Pipeline", "Key People"}
    return text not in skip and len(text.split()) <= 4


def _get_section(markdown: str, header_pattern: str) -> str | None:
    pattern = re.compile(
        rf"(?:^|\n)#+\s*.*?{header_pattern}.*?\n(.*?)(?=\n#+\s|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(markdown)
    if match:
        return match.group(1)
    return None


ROLE_KEYWORDS = [
    "Partner", "Principal", "Managing Director", "Director",
    "Senior Manager", "Manager", "Senior Associate", "Associate",
    "Engagement Leader", "Engagement Manager",
]

ROLE_PATTERN = re.compile(
    r"(?:" + "|".join(re.escape(r) for r in ROLE_KEYWORDS) + r")",
    re.IGNORECASE,
)

OFFICE_PATTERN = re.compile(
    r"(?:(?:based\s+in|office|location|from)\s*[:;]?\s*)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
    r"|(?:,\s+|\()\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*(?:\)|,|$)"
)


def _extract_role_and_office_near(text: str, pos: int, name: str) -> tuple[str | None, str | None]:
    """Look at the ~200 chars after a name match to find role and office."""
    window = text[pos:pos + 200]

    role = None
    role_match = ROLE_PATTERN.search(window)
    if role_match:
        role = role_match.group(0)
        role = role[0].upper() + role[1:]

    office = None
    office_match = OFFICE_PATTERN.search(window)
    if office_match:
        office = (office_match.group(1) or office_match.group(2) or "").strip()
        if office and office.lower() in {"the", "a", "an", "and", "or", "with", "for"}:
            office = None

    return role, office
