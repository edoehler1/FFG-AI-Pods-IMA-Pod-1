# Current Implementation Plan

## Status: Phases 0–3B COMPLETE

Branch: `feature/mcp-integration-and-dashboard`

---

## What's Done

### Phase 0: Bug Fixes
- `ingestion/run.py` — fixed signal.id captured before commit (flush before collecting IDs)
- `ingestion/sources/sec_financials.py` — fixed broken TARGET_COMPANIES import (local CIK_MAP)
- `backend/requirements.txt` — added anthropic>=0.52.0
- `frontend/src/utils/formatters.ts` — wrapped markdownToHtml with DOMPurify.sanitize()
- `frontend/package.json` — added dompurify + @types/dompurify

### Phase 1: Salesforce Pipeline Enricher
- `ingestion/enrichment/salesforce_enricher.py` — new enricher, mcp_source="salesforce", stale_days=7
- `ingestion/enrich.py` — registered SalesforceEnricher in COMPANY_ENRICHERS
- `backend/app/services/enrichment_reader.py` — added Salesforce Pipeline section to build_enrichment_context()
- `frontend/src/components/companies/CompanyEnrichments.tsx` — added source label + color
- `backend/app/services/signal_matcher.py` — injected salesforce data into _get_enrichment_snippet()

### Phase 2A: People Connector Engagement Enricher
- `ingestion/enrichment/people_connector_enricher.py` — new enricher using engagement_client_finder, mcp_source="people_engagements", stale_days=30
- Registered in enrich.py, enrichment_reader.py, and CompanyEnrichments.tsx (same pattern as Salesforce)

### Phase 2B: Relationship Service + Frontend Tab
- `backend/app/services/relationship_service.py` — reads cached People Connector enrichment + manual contacts/engagements
- `backend/app/api/relationships.py` — GET /companies/{id}/relationships and /relationships/prompts
- `backend/app/api/router.py` — wired relationships router
- `frontend/src/components/companies/CompanyRelationships.tsx` — shows PwC Engagement History, Manual Contacts, Past Engagements
- `frontend/src/pages/CompanyDetailPage.tsx` — added "Relationships" tab (second tab after Overview)

### Phase 2C: Inject People Data into Signal Matching
- `backend/app/services/signal_router.py` — Stage 5: maps signal-company matches → who at PwC should act (GRP > account team > recent staff > manual contacts)
- `backend/app/services/signal_matcher.py` — talking points prompt updated to reference PwC people and Salesforce pipeline when available

---

## What's Next

### Phase 3A: Dashboard Page — COMPLETE
- `backend/app/api/dashboard.py` — GET /api/dashboard with top_actions, portfolio_pulse, pipeline_summary
- Wired into `backend/app/api/router.py`
- `frontend/src/pages/DashboardPage.tsx` — three sections: Top Actions Today, Portfolio Pulse (grouped by status), Pipeline Summary (Salesforce)
- `frontend/src/App.tsx` — DashboardPage is default route (/), Signals moved to /signals
- `frontend/src/components/layout/Sidebar.tsx` — Dashboard as first nav item

### Phase 3B: Outreach Queue Page — COMPLETE
- `backend/app/models/outreach_action.py` — OutreachAction model (id, signal_company_match_id, status, timestamps)
- `backend/app/services/outreach_ranker.py` — composite scoring: match_score (50%) + signal_recency (30%) + relationship_strength (20%)
- `backend/app/api/outreach.py` — GET /api/outreach (ranked queue, status filter), POST /api/outreach/{match_id}/feedback (acted_on/saved/dismissed)
- Wired into `backend/app/api/router.py` (now 40 routes)
- `frontend/src/pages/OutreachPage.tsx` — Queue/Saved/Acted On/Dismissed tabs, urgency badges, expandable talking points, action buttons
- `frontend/src/App.tsx` — /outreach route
- `frontend/src/components/layout/Sidebar.tsx` — "Outreach" nav item (second after Dashboard)

---

## Key Files to Reference

- `backend/app/services/signal_router.py` — the routing logic that connects signals → companies → PwC people
- `backend/app/services/enrichment_reader.py` — central data-access layer for all enrichment data
- `backend/app/services/signal_matcher.py` — the 4-stage matching pipeline (signal_router is Stage 5)
- `backend/app/models/signal_company.py` — SignalCompanyMatch model (signal_id, company_id, match_score, match_type, talking_points)
- `backend/app/models/weekly_report.py` — WeeklyReport model (has_opportunity flag)
- `frontend/src/pages/CompanyDetailPage.tsx` — reference for tab/component patterns
- `frontend/src/components/signals/SignalCard.tsx` — reference for signal display patterns
- `frontend/src/App.tsx` — routing setup
- `frontend/src/components/layout/Sidebar.tsx` — navigation

## Verification

- **Phase 3A:** Start backend, navigate to /, verify dashboard loads with top actions and portfolio pulse
- **Phase 3B:** Navigate to /outreach, verify ranked cards display, test action buttons
