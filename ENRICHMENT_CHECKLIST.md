# People Connector Enrichment Checklist

Step-by-step guide for populating a company's Relationships tab with real PwC data. Follow this exactly for every company.

---

## Prerequisites

- Claude Code session with People Connector MCP tools available
- Backend running (`python -m uvicorn app.main:app --port 8000`)
- Company already exists in the database

---

## Step 1: Find All Entity IDs

The same company often has multiple entities in PwC's system (e.g., Aptiv Services US, Aptiv Corporation, Aptiv PLC). Search broadly first.

```
Call: engagement_client_finder
  client_name: "<Company Name>"
  group_by: "engagement"
  time_range: "last_24mo"
  limit: 10
```

Check the response:
- Look at `disambiguation_options[]` for all entity variants
- Note the `client_id` for each entity
- Note the GRP from `facets.client_master[].global_relationship_partner_name`
- Note `client_external_team_members` for client-side contacts

**If the company resolved to the wrong entity** (e.g., a subsidiary in Mexico), re-call with each `client_id` from disambiguation_options until you find the right one(s).

---

## Step 2: Pull Advisory Engagements from ALL Entities

**IMPORTANT: We ONLY want Advisory engagements. No Assurance, no Audit, no Tax compliance.**
The Relationships tab is for Strategy& partners — they do not care about audit work.

For each entity ID that has engagements:

```
Call: engagement_client_finder
  client_id: "<entity_id>"
  group_by: "engagement"
  los: "Advisory"
  time_range: "last_24mo"
  limit: 15
```

**Use `los: "Advisory"` ALWAYS.** This filters out Assurance (audit), Tax, and Internal Firm Services.

If `los=Advisory` returns zero, that means the company has no advisory engagements — that IS the correct answer. Do NOT fall back to an unfiltered call and include audit engagements. If there's no advisory work, the Relationships tab will show just the GRP and "No Strategy& engagements" / no Other Advisory sections. That's fine.

Optionally, try without `los` filter ONLY to discover the GRP and client_master data (Step 1), never to populate engagements:

```
Call: engagement_client_finder
  client_id: "<entity_id>"
  group_by: "engagement"
  time_range: "last_24mo"
  limit: 10
```

From each engagement, extract:
- Engagement name
- Service line (from `projects[].service_line`)
- Start date, end date
- Status: open (end_date in future or null) vs closed
- Staff: ONLY Principals, Partners, Directors, Managing Directors (check `business_title` or `role`)
- Staff formal_role if available (Engagement Leader, Engagement Manager, etc.)

---

## Step 3: Look Up Emails for Principals and Directors

For each unique Principal/Director found across all engagements:

```
Call: find_people
  name: "<Full Name>"
```

Extract from the response:
- `email`
- `title` (their actual PwC title)
- `office_location`
- `practice` (their sub-practice path, e.g., "Advisory > Consulting Solutions > Strategy")

Also look up the GRP if not already done.

**Only look up Principals and Directors.** Do not look up Managers, Senior Associates, or below.

**Every Principal and Director MUST have an email.** If find_people returns no profile, the entity_resolution response often has the email in `normalized_id`. No Director/Principal should show on the Relationships tab without a clickable email.

---

## Step 4: Build Structured Data

Build the JSON summary following this exact schema:

```json
{
  "summary_text": "GRP: Name (Role, Office). N engagements (M open). N senior staff.",
  "grp": {"name": "...", "role": "Principal, Practice", "office": "City", "email": "...@pwc.com"},
  "account_team": [],
  "engagement_staff": [
    {"name": "...", "role": "Principal, Practice", "office": "City", "email": "...@pwc.com"}
  ],
  "engagements": [
    {
      "name": "Engagement Name",
      "service_line": "Service Line Name",
      "description": "1-2 sentence description of what this engagement does",
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "status": "open" or "closed",
      "staff_count": N,
      "key_staff": [
        {"name": "...", "role": "Principal, Engagement Leader", "email": "...@pwc.com"}
      ]
    }
  ],
  "total_people_count": N,
  "has_grp": true/false,
  "has_account_team": false,
  "filter": "Note about which entities were searched"
}
```

**Rules:**
- Engagements sorted newest-first by start_date
- key_staff includes ONLY Principals/Directors with their formal_role where available
- Descriptions should explain what the engagement actually does, not just repeat the name
- Strategy& engagements are tagged by service_line containing "strategy", "consulting", "cost structure", "value realization", "manufacturing strategy"
- Include data from ALL entity IDs for this company
- `account_team` is always empty (we don't display CRM account team per Gabriel's preference)

---

## Step 5: Store in Database

Use the parser script or store directly:

```python
import json, uuid, sys, os
from datetime import datetime, timedelta

sys.path.insert(0, "backend")
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.mcp_enrichment import MCPEnrichment

engine = create_engine("sqlite:///data/signals.db", connect_args={"check_same_thread": False})
db = sessionmaker(bind=engine)()

COMPANY_ID = "<uuid from companies table>"

# Build markdown from the structured data (or use build_markdown from scripts/parse_engagement_data.py)
markdown = "..."  # readable version
summary = {...}   # the JSON from Step 4

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
        id=str(uuid.uuid4()),
        entity_type="company",
        entity_id=COMPANY_ID,
        mcp_source="people_engagements",
        query_prompt=f"PwC advisory engagement history for <Company Name>",
        response_markdown=markdown,
        response_summary=json.dumps(summary),
        fetched_at=now,
        stale_after=now + timedelta(days=30),
    ))
db.commit()
db.close()
```

---

## Step 6: Verify

1. Restart backend (or wait for hot-reload)
2. Open the company's detail page → Relationships tab
3. Check:
   - [ ] GRP shows with email and role badge
   - [ ] Strategy& engagements section shows relevant engagements (if any)
   - [ ] Each engagement has: name, OPEN/CLOSED badge, dates, service line, description
   - [ ] Each engagement shows Principals/Directors with emails (clickable mailto links)
   - [ ] Other Advisory section is collapsible with correct grouping
   - [ ] Engagements are in chronological order (newest first)
   - [ ] No "Account Team Member" generic labels — everyone has their actual PwC title
   - [ ] Client-Side Contacts at bottom shows placeholder note (seed data)

---

## Companies Status

| Company | Status | GRP | Entities Checked |
|---|---|---|---|
| Aptiv | DONE | Daniel O'Neill | 455400, 39008461, 120791567, 119864667, 119082748 |
| Ford Motor Company | DONE | Maura E DePrisco | 27951 |
| Boeing Company | DONE | Chris Tierney | 1099 (Advisory only) |
| Lockheed Martin | DONE | Holly R McKenzie | 143079 (Advisory only) |
| General Motors | DONE | C.J. Finn | 512 umbrella (Advisory only) |
| Northrop Grumman | DONE | Daniel C Dipillo | 75813311 (Advisory only) |
| General Dynamics | PARTIAL (15 missing emails) | Benjamin R Towne | Advisory only, needs email lookups |
| L3Harris Technologies | DONE | unknown | 701618 (Advisory only) |
| RTX Corporation | DONE | unknown | 5212 (1 advisory eng only) |
| Stellantis | NEEDS PROCESSING | Marc Gerretsen | 118422325 (NV), try FCA US LLC too |
| Tesla Inc | NEEDS PROCESSING | Robert Conklin | 816894 |
| Rivian Automotive | NEEDS PROCESSING | C.J. Finn | 107697027, 117806521 |
| Magna International | NEEDS PROCESSING | unknown | 846912 |
| Bosch | NO DATA | Marcus Nickel (German) | 0 US engagements |
| Chevron Corporation | DONE | Rowena Cipriano-Reyes | 2277 (Advisory only) |
| ExxonMobil | NEEDS PROCESSING | Simon J Tait | 39225 |
| Shell plc | NEEDS PROCESSING | unknown | 4777 (Shell USA) |
| Duke Energy | NEEDS PROCESSING | unknown | 133035 |
| NextEra Energy | NEEDS PROCESSING | Blake Cooper | 496238 |
| Enbridge Inc | NEEDS PROCESSING | Alodie Brew | 263933 (US), 21473117, 8210 |
