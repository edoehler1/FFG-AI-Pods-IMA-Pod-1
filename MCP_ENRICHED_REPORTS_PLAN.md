# Plan: MCP-Enriched Weekly Reports

**Branch:** `feature/mcp-integration-and-dashboard`
**Status:** Phases 0–3B of the previous plan are COMPLETE. This is the next major feature.
**Authors:** Gabriel Solis, Ethan Doehler

---

## Context

The platform's weekly reports currently use only 4 of 14 available MCP data sources, output unstructured markdown, and have zero personalization. The end goal is a weekly partner update that:

- Shows top signals per company — only companies with actual meaningful news
- Cross-references news against financial baselines from the company profile
- Surfaces who at PwC should act (GRP, account team, engagement staff — by name, not just "engagement history exists")
- Ties into Salesforce pipeline (active opportunities, deal stage, value)
- Is filtered to the partner's portfolio — the companies they work with and monitor

**Report format:** Top signals with brief overview + opportunity flag, then ability to "double click" into each for the full story.

---

## What Already Exists (don't rebuild these)

- **14 MCP enrichers** already wired up in `ingestion/enrich.py` (CapIQ, BoardEx, Earnings, EMIS, Factiva, Web, SEC risk/MDA, Salesforce, People Connector, IBISWorld, ConnectedSource, VIM, CEO Survey)
- **`enrichment_reader.build_enrichment_context()`** — assembles ALL 14 sources into a single prompt-ready string. This is the key function.
- **`CompanyProfile.financial_summary`** — contains SEC XBRL data (revenue, margins, etc.) from the profile builder
- **`signal_router.py`** — Stage 5 of the matching pipeline, routes signals → companies → PwC people
- **Weekly report agent** (`weekly_report_agent.py`) — generates per-company reports, but only uses 4 MCP sources (factiva, earnings, boardex, connectedsource). The other 10 are ignored.
- **Dashboard** and **Outreach Queue** pages — already built, already use signal routing and enrichment data

---

## Phase 1: Feed All MCP Data into Weekly Reports

**The highest-value change with the least risk.** One file change.

### What to do

**File: `backend/app/services/weekly_report_agent.py`**

1. **Replace the 4 individual enrichment calls** (lines 123-127) with one call:
   ```python
   from app.services.enrichment_reader import build_enrichment_context
   enrichment_context = build_enrichment_context(db, company.id, company.industry)
   # Cap at ~6000 chars to manage token budget
   if len(enrichment_context) > 6000:
       enrichment_context = enrichment_context[:6000] + "\n[...truncated]"
   ```

2. **Pull the financial baseline** from the company profile:
   ```python
   financial_baseline = profile.financial_summary if profile else None
   ```

3. **Revise the LLM prompt** to include:
   - Full enrichment context block (replaces the 4 individual sections)
   - Financial baseline as a separate section from the profile narrative
   - Explicit financial cross-referencing instruction
   - "Who Should Act" section that names specific PwC people
   - Salesforce pipeline framing

4. **Expand the report template** from 4 sections to 6:
   - `## What Happened This Week`
   - `## Why It Matters` — financial cross-reference: "Compare news to the financial baseline. Does it accelerate a known trend, contradict it, or create a new financial implication? Cite specific numbers."
   - `## PwC Context` — "If PwC engagement data is present, name the GRP and account team by name and office. If Salesforce pipeline data exists, note the deal stage."
   - `## The Opportunity`
   - `## Who Should Act` — "Name the specific PwC person who should lead. Priority: GRP > account team > recent engagement staff > manual contacts."
   - `## Recommended Action`

5. **Increase limits:** `max_tokens` from 1500 → 2000, profile context cap from 1500 → 2500 chars.

### How to verify
```bash
# Start backend
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# Generate weekly reports
curl -X POST http://localhost:8000/api/reports/weekly/generate

# Check a report for a company with enrichment data (e.g., Ford)
curl http://localhost:8000/api/reports/weekly?has_opportunity=true&limit=3 | python -m json.tool
```

Check that the report:
- Names specific PwC people (not just "PwC has engagement history")
- References financial numbers from the baseline
- Mentions Salesforce pipeline if data exists
- Has all 6 sections

---

## Phase 2: Summary + Drill-Down Report Structure

**Makes reports scannable.** Currently each report is a single markdown blob. Goal: collapsed summary → expand for full story.

### What to do

**File: `backend/app/models/weekly_report.py`** — add nullable columns:
```python
urgency: Mapped[str | None] = mapped_column(String(10))           # high/medium/low
opportunity_summary: Mapped[str | None] = mapped_column(Text)     # 1-2 sentence elevator pitch
suggested_lead: Mapped[str | None] = mapped_column(Text)          # JSON: {"name": "...", "role": "GRP", "office": "..."}
financial_cross_ref: Mapped[str | None] = mapped_column(Text)     # financial cross-reference paragraph
top_signal_title: Mapped[str | None] = mapped_column(Text)        # headline of most important signal
```

**SQLite gotcha:** `create_all()` won't add columns to an existing table. Add a startup helper in `weekly_report_agent.py`:
```python
from sqlalchemy import text

def _ensure_columns(db):
    new_cols = [
        ("urgency", "VARCHAR(10)"),
        ("opportunity_summary", "TEXT"),
        ("suggested_lead", "TEXT"),
        ("financial_cross_ref", "TEXT"),
        ("top_signal_title", "TEXT"),
    ]
    for col_name, col_type in new_cols:
        try:
            db.execute(text(f"ALTER TABLE weekly_reports ADD COLUMN {col_name} {col_type}"))
            db.commit()
        except Exception:
            db.rollback()  # column already exists
```

**File: `backend/app/services/weekly_report_agent.py`** — after LLM response:
- Parse sections by splitting on `## ` headers
- Extract urgency from an explicit `URGENCY: high/medium/low` line (add this to the prompt)
- Extract suggested lead from a `LEAD: Name (Role, Office)` line
- Extract the "What Happened" section as `top_signal_title`
- Extract "The Opportunity" section as `opportunity_summary`
- Populate the new model fields alongside `content`

**File: `backend/app/api/reports.py`**:
- Return new fields in weekly report list/detail responses
- Add `GET /api/reports/weekly/summary` — returns only summary fields (no full content) for a fast scannable list

**File: `frontend/src/pages/ReportsPage.tsx`**:
- **Collapsed view:** company name, urgency badge, opportunity_summary, suggested_lead badge, signal count
- **Expanded view:** full markdown with styled sections
- Falls back to current rendering for old reports without structured fields

### How to verify
- Regenerate reports, check API response includes new fields
- Frontend shows collapsed summaries that expand to full story
- Old reports still render correctly (graceful fallback)

---

## Phase 3: Partner Portfolio Filtering

**Personalization without auth.** Partners have already added their companies to the platform. This phase adds a name-based filter so they see only "their" companies.

### What to do

**New file: `backend/app/services/partner_context.py`**:
```python
def resolve_partner_companies(db, partner_name: str) -> list[str]:
    """Search cached People Connector data for companies linked to this partner."""
    enrichments = db.query(MCPEnrichment).filter(
        MCPEnrichment.mcp_source == "people_engagements",
        MCPEnrichment.entity_type == "company",
    ).all()
    
    matched_ids = []
    name_lower = partner_name.lower()
    for e in enrichments:
        if name_lower in (e.response_markdown or "").lower():
            matched_ids.append(e.entity_id)
    return matched_ids
```

**File: `backend/app/api/reports.py`**:
- Add `partner_name` query param to `GET /reports/weekly` — filters to companies where that name appears in People Connector enrichment data
- Add `industry` query param — filters by company industry
- Both stack: partner + industry = that partner's companies in that industry

**File: `frontend/src/pages/ReportsPage.tsx`**:
- Add "Partner" text input + "Find My Companies" button at top of weekly reports tab
- Add industry dropdown (Automotive / A&D / Energy / All)
- When partner name is active, show banner: "Showing {N} companies linked to {partner_name}"
- Clear button to reset

### How to verify
- Run MCP enrichment for People Connector (`python -m ingestion.enrich --mcp people_engagements`)
- Enter a partner name that appears in the enrichment data
- Confirm the report list filters correctly
- Test industry filter independently and in combination

---

## Phase 4 (Future — after partner feedback)

Not building now. Capturing for later:

- **Salesforce OAuth** — partner authenticates once, system auto-pulls their pipeline
- **Network-aware routing** — `find_people(network_scope="__caller__")` to show "people in YOUR network who work with this company"
- **Warm intro suggestions** — `network_relationships(mode="warm_intro")` when the partner doesn't know the GRP
- **Meeting prep** — `network_relationships(mode="meeting_prep")` to brief partner before a call
- **Per-partner report framing** — LLM prompt includes the partner's own engagement history and tailors the recommended action

These require auth or a persistent "current partner" selection.

---

## Key Reference Files

| File | What it does |
|---|---|
| `backend/app/services/weekly_report_agent.py` | Core report generation — **the main file to change** |
| `backend/app/services/enrichment_reader.py` | `build_enrichment_context()` — assembles all 14 MCP sources. Already correct, just call it. |
| `backend/app/models/weekly_report.py` | WeeklyReport model — add structured columns in Phase 2 |
| `backend/app/models/company_profile.py` | Has `financial_summary` field — the financial baseline |
| `backend/app/services/signal_router.py` | Stage 5 — routes signals to PwC people. Used by dashboard/outreach already. |
| `backend/app/api/reports.py` | Report endpoints — add structured fields + filters |
| `backend/app/services/partner_context.py` | New in Phase 3 — partner name → company resolution |
| `frontend/src/pages/ReportsPage.tsx` | Report UI — summary/drill-down + partner filter |
| `ingestion/enrich.py` | MCP enrichment CLI — run this to populate enrichment data before testing |
| `CURRENT_PLAN.md` | Previous plan — Phases 0-3B are complete |
| `BUILDERS_GUIDE.md` | Full project context, known bugs, how to run locally |

---

## How to Run Locally

```bash
# Backend
cd backend
../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
node_modules\.bin\vite.cmd

# Ingestion (populate signal data)
cd backend
../.venv/Scripts/python -m ingestion.run news
../.venv/Scripts/python -m ingestion.run sec_edgar

# MCP enrichment (list what needs populating)
cd backend
../.venv/Scripts/python -m ingestion.enrich

# Seed database (if starting fresh)
cd backend
../.venv/Scripts/python seed.py
```

---

## Uncommitted Work on This Branch

Everything from the previous plan (Phases 0-3B) is uncommitted. Before starting this plan, you may want to commit the current state. Here's what's pending:

**Bug fixes:** run.py signal ID fix, sec_financials.py import fix, anthropic in requirements, DOMPurify XSS fix

**New files:**
- `backend/app/api/dashboard.py` — Dashboard API
- `backend/app/api/outreach.py` — Outreach API
- `backend/app/api/relationships.py` — Relationships API
- `backend/app/models/outreach_action.py` — OutreachAction model
- `backend/app/services/outreach_ranker.py` — Outreach ranking
- `backend/app/services/relationship_service.py` — Relationship data assembly
- `backend/app/services/signal_router.py` — Signal → PwC person routing
- `frontend/src/pages/DashboardPage.tsx` — Dashboard page (default route)
- `frontend/src/pages/OutreachPage.tsx` — Outreach queue page
- `frontend/src/components/companies/CompanyRelationships.tsx` — Relationships tab
- `ingestion/enrichment/people_connector_enricher.py` — People Connector enricher
- `ingestion/enrichment/salesforce_enricher.py` — Salesforce enricher

**Modified files:** router.py, enrichment_reader.py, signal_matcher.py, enrich.py, CompanyEnrichments.tsx, CompanyDetailPage.tsx, App.tsx, Sidebar.tsx, formatters.ts, package.json
