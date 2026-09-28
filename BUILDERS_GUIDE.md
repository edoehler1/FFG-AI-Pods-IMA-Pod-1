# Sales Intelligence Platform — Builder's Guide

**Last updated:** 2026-09-28 (evening)
**Contributors:** Gabriel Solis, Ethan Doehler (IMA AI Pod)
**Status:** Demo-stage MVP. Core loop functional. MCP enrichment pipeline complete. Weekly reports use all 14 MCP sources with structured summaries. Not production-ready.

---

## 1. What this project is

A signal intelligence and relationship matching tool for Strategy& partners covering automotive, aerospace & defense, and energy. It answers five questions daily:

1. **What just happened?** — Market signals relevant to the partner's portfolio.
2. **Who does it affect?** — Which companies and contacts are impacted.
3. **What should I pitch?** — Which S& capabilities align to the signal.
4. **When should I reach out?** — Urgency based on signal recency and relationship warmth.
5. **What do I say?** — Draft talking points connecting the signal, the relationship, and the S& value proposition.

The core thesis: partners already track signals, relationships, and capabilities — but in their heads, email, and scattered files. This tool connects those three streams and surfaces the highest-value outreach opportunities.

**This is a demo-scope build.** The goal is to demonstrate the concept to partners and pod leadership with real data and a working UI — not to ship enterprise software. Every decision should optimize for demo credibility, not production scale.

---

## 2. Tech stack

| Component | Technology | Notes |
|---|---|---|
| Backend | Python 3.12 / FastAPI / SQLAlchemy | ~30+ real API endpoints across 11 routers |
| Frontend | TypeScript / React 19 / Vite 8 / Tailwind CSS v4 | 7 pages, all wired to real backend |
| Database | SQLite (dev) | PostgreSQL planned for prod. No Alembic migrations — `create_all()` on startup + runtime `ALTER TABLE` for new columns. |
| LLM | Claude API (Anthropic) via configurable gateway | Dual-mode client: OpenAI-compatible gateway (httpx) + native Anthropic SDK |
| Ingestion | Python CLI runner | 7 live data sources. No Celery/task queue — synchronous only. |
| MCP Enrichment | 14 enrichers wired to PwC MCP servers | Company-level (10) + Industry-level (4). CLI runner in `ingestion/enrich.py`. |
| Infrastructure | Local dev only | No Docker, no deployment pipeline. CORS origins configurable via env var. |

---

## 3. File structure (as of 09-28)

```
FFG-AI-Pods-IMA-Pod-1/
├── backend/
│   ├── app/
│   │   ├── main.py                         # FastAPI app, CORS (configurable), startup categorization, project-root path setup
│   │   ├── config.py                       # Settings from .env (DB URL, API keys, model name, CORS origins)
│   │   ├── database.py                     # SQLAlchemy engine, SessionLocal, Base
│   │   ├── api/
│   │   │   ├── router.py                   # Mounts all 11 sub-routers under /api
│   │   │   ├── companies.py                # CRUD + intelligence + analysis + profiles + sort/filter + cascade delete
│   │   │   ├── contacts.py                 # Full CRUD scoped to company
│   │   │   ├── engagements.py              # List + Create (no update/delete yet)
│   │   │   ├── signals.py                  # Signal browsing: all, portfolio, discovery + categorize (shared filter helper)
│   │   │   ├── reports.py                  # Weekly reports (summary + detail endpoints) + on-demand briefs
│   │   │   ├── profiles.py                 # Company profile CRUD + generation (returns all fields)
│   │   │   ├── upload.py                   # CSV/XLSX/PDF/DOCX bulk import
│   │   │   ├── enrichments.py              # MCP enrichment CRUD (POST, GET, GET by company, DELETE)
│   │   │   ├── relationships.py            # GET relationships + relationship prompts per company
│   │   │   ├── dashboard.py                # Top actions, portfolio pulse, pipeline summary (structured + staleness-filtered)
│   │   │   └── outreach.py                 # Outreach queue + feedback (acted_on/saved/dismissed)
│   │   ├── models/
│   │   │   ├── company.py, contact.py, engagement.py
│   │   │   ├── signal.py                   # Includes news_category column (importance_score removed)
│   │   │   ├── signal_company.py           # Match junction with unique constraint on (signal_id, company_id)
│   │   │   ├── company_analysis.py, company_profile.py
│   │   │   ├── weekly_report.py            # Includes structured fields: urgency, opportunity_summary, suggested_lead, financial_cross_ref, top_signal_title
│   │   │   ├── mcp_enrichment.py           # Indexed entity lookup with staleness support
│   │   │   └── outreach_action.py          # FK to signal_company_matches, tracks feedback
│   │   ├── schemas/                        # Pydantic schemas (company, contact, engagement, signal, enrichment)
│   │   └── services/
│   │       ├── signal_matcher.py           # 4-stage pipeline: name→industry→LLM→talking points (overflow capped at 0.5)
│   │       ├── signal_router.py            # Stage 5: routes signals → companies → PwC people + pipeline summary
│   │       ├── signal_categorizer.py       # LLM + keyword categorization (SEC filings → company_moves, not regulatory)
│   │       ├── signal_summarizer.py        # Type/category breakdown utility
│   │       ├── relevance_scorer.py         # Domain blocklist (PR wires allowed) + Claude quality scoring
│   │       ├── onboarding.py               # Auto-pipeline on company creation
│   │       ├── company_analyzer.py         # Intelligence aggregation + LLM analysis
│   │       ├── financial_analyzer.py       # SEC XBRL data + LLM analysis (CIK_LOOKUP from sec_edgar — single source of truth)
│   │       ├── profile_builder.py          # Comprehensive company profile generation
│   │       ├── weekly_report_agent.py      # Per-company weekly intelligence — uses ALL 14 MCP sources, 6-section template, structured field parsing
│   │       ├── report_generator.py         # Portfolio-wide signal briefs
│   │       ├── enrichment_reader.py        # build_enrichment_context() — assembles all 14 MCP sources, expanded industry slug normalization
│   │       ├── outreach_ranker.py          # Composite scoring with batch-prefetched queries, pipeline summary pass-through
│   │       ├── relationship_service.py     # People Connector + manual contacts + engagements unified
│   │       ├── taxonomy.py                 # S& capability taxonomy loader
│   │       ├── upload_parser.py            # Multi-format parser (CSV/XLSX/PDF/DOCX)
│   │       └── llm_client.py              # Dual-mode Claude client (httpx, proper SSL)
│   ├── seed.py                             # DB seeder (companies, contacts, matching)
│   ├── seed_data/                          # capability_taxonomy.json, sample CSVs
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                         # Routing with 404 catch-all
│   │   ├── api/                            # Axios clients: companies, contacts, engagements, signals, reports, upload, enrichments, dashboard, outreach
│   │   ├── components/
│   │   │   ├── common/                     # FilterPanel, FileUploader, SignalSummaryBadge
│   │   │   ├── companies/                  # Card, List, Form, Analysis, Profile, Filings, News, IndustryNews, Enrichments (with citations), Relationships (with engagement notes)
│   │   │   ├── contacts/                   # ContactForm (inline add modal)
│   │   │   ├── engagements/                # EngagementForm (inline add modal)
│   │   │   ├── signals/                    # SignalCard (with relevance gradient), SignalList, FilingsView
│   │   │   └── layout/                     # Header, Sidebar
│   │   ├── hooks/                          # useCompanies, useCompany, useSignals, useDebouncedValue
│   │   ├── pages/                          # SignalsPage, CompaniesPage, CompanyDetailPage, ReportsPage, UploadPage, DashboardPage, OutreachPage
│   │   ├── types/                          # company, contact, engagement, signal, dashboard, outreach
│   │   └── utils/                          # constants.ts (industries, sub-sectors, sizes), formatters.ts (markdownToHtml w/ DOMPurify)
│   ├── package.json, vite.config.ts
│   └── index.html                          # Title: "Sales Intelligence Platform"
├── ingestion/
│   ├── run.py                              # CLI: python -m ingestion.run --source <source>
│   ├── enrich.py                           # CLI: python -m ingestion.enrich — runs all 14 MCP enrichers
│   ├── config.py                           # API keys, industry keyword lists (all 3 verticals)
│   ├── sources/                            # 8 source clients (news_rss, sec_edgar, sec_financials, federal_register, gdelt, sam_gov, usaspending, event_registry)
│   ├── processing/                         # classifier.py (keyword, density-based tie resolution), deduplication.py (SHA-256, date-normalized)
│   └── enrichment/                         # 14 MCP enrichers (see section 4 for full list)
├── data/signals.db                         # SQLite database
├── .env                                    # API keys and config (never committed)
├── Sales_Intelligence_Platform_Project_Plan.md   # Full product spec
├── Technical_Reference_File_Structure.md         # Original file tree by phase (partially outdated)
├── MCP_ENRICHED_REPORTS_PLAN.md                  # Plan for MCP-enriched weekly reports (Phases 1-2 DONE, Phase 3 pending)
├── CLAUDE.md                               # Coding conventions, git workflow
└── BUILDERS_GUIDE.md                       # This file
```

---

## 4. What is done

### Ingestion — 7 live data sources, all hitting real APIs
- Google News RSS (company-specific + 25 industry queries + 3 supplemental defense/space feeds)
- SEC EDGAR filings (10-K, 10-Q, 8-K, DEF 14A with per-type caps)
- Federal Register (NHTSA, FAA, DoD, EPA, FERC, DOE, NRC — all 3 verticals covered)
- GDELT news (top 30 keywords across auto, A&D, energy)
- SAM.gov contracts (requires API key)
- USASpending awards
- Event Registry (top 30 keywords, requires API key)
- Keyword-based industry/sub-sector/type classification with density-based tie resolution
- SHA-256 title dedup (date-normalized, handles missing dates)
- Source credibility domain blocklist (PR wires like prnewswire, businesswire, globenewswire allowed — they carry official corporate announcements)

### MCP Enrichment — 14 sources wired and functional
All enrichers built in `ingestion/enrichment/`, orchestrated via `ingestion/enrich.py`.

**Company-level (10):**
- CapIQ (financials, profile)
- BoardEx (executive/director profiles)
- Earnings (call transcripts, takeaways)
- EMIS (ownership, structure)
- Factiva (licensed press coverage)
- Web (open-web cross-check)
- SEC MCP Risk (risk factors from filings)
- SEC MCP MD&A (management discussion from filings)
- Salesforce (advisory/strategy pipeline only — excludes audit, tax, assurance. Structured extraction: opportunity names, values, stages, close dates, owners)
- People Connector (GRP, account team, engagement staff)

**Industry-level (4):**
- IBISWorld (sector reports)
- ConnectedSource (PwC insights)
- VIM (Value in Motion research)
- CEO Survey (Global CEO Survey findings)

`enrichment_reader.build_enrichment_context()` assembles all 14 into a single prompt-ready string with expanded industry slug normalization (16 variants across all 3 verticals).

### Backend — ~30+ API endpoints across 11 routers
- **Companies:** Full CRUD, sort/filter (name, industry, status, created_at), search. Cascade delete cleans up all related records (matches, outreach actions, reports, analyses, profiles, enrichments).
- **Contacts:** Full CRUD scoped to company
- **Engagements:** List + Create (no update/delete)
- **Signals:** List with filters (industry, sub-sector, type, category, source), portfolio view (matched to active/past clients), discovery view (unmatched). Shared filter helper eliminates duplicated logic.
- **Reports:** Weekly per-company reports with structured fields (urgency, opportunity_summary, suggested_lead, financial_cross_ref, top_signal_title). Summary endpoint (lightweight, no content blob) + detail endpoint (full content). On-demand portfolio briefs with actual date ranges.
- **Profiles:** Company profile generation via LLM. Returns financial_summary, news_summary, and profile_narrative.
- **Upload:** CSV, XLSX, PDF, DOCX with flexible header aliasing
- **Enrichments:** Full CRUD for MCP enrichment records
- **Relationships:** PwC engagement data + manual contacts + engagements unified per company
- **Dashboard:** Top actions (with PwC engagement context and pipeline badges), portfolio pulse (with last report date), pipeline summary (structured Salesforce data with 14-day staleness filter)
- **Outreach:** Prioritized outreach queue with batch-prefetched queries (~6 total queries instead of ~800). Pipeline summary pass-through. Feedback (acted on / saved / dismissed) with error reporting.
- **On startup:** auto-categorizes signals — SEC filings → company_moves (not regulatory), USASpending → general. Renames legacy "competitors" to "company_moves".

### Signal matching pipeline (the core intelligence)
1. **Name match** — regex word-boundary search against `SHORT_NAMES` dict (27 companies). Ambiguous names (Ford, Shell, GM, Magna, AES) require industry + business context words to score above 0.5 threshold. Non-SEC signals filtered through consumer content blocklist and domain blocklist.
2. **Industry match** — same-industry signals matched to companies with sub-sector relationship awareness. Value chain relationships mapped (OEM-supplier, prime-subcontractor, upstream-midstream, etc.) — not everyone in the same industry is a competitor.
3. **LLM relevance filter** — Claude scores industry-match candidates 0.0-1.0 using 500-char body snippets. Threshold: 0.4. Overflow candidates beyond LLM batch cap (160) filtered to match_score >= 0.5 instead of passing all through.
4. **Talking points** — Claude generates 3-4 bullets per match incorporating company context (client status, notes, size, geography, S& capabilities). Framing adapted to relationship status: target = pitch, active = deepen, past = re-engage. Template fallback when LLM unavailable.
5. **Signal routing** — Routes matched signals to specific PwC people via People Connector data. Priority: GRP > account team > engagement staff > manual contacts. Includes pipeline summary from Salesforce.

### Weekly reports (MCP-enriched, Phase 1+2 complete)
- Uses ALL 14 MCP sources via `build_enrichment_context()` (previously only 4)
- Financial baseline from company profile (SEC XBRL) cross-referenced against news
- 6-section LLM template: What Happened, Why It Matters, PwC Context, The Opportunity, Who Should Act, Recommended Action
- Structured field parsing: urgency (high/medium/low), opportunity_summary, suggested_lead (JSON with name/role/office), financial_cross_ref, top_signal_title
- Summary endpoint for fast list view (no content blob)
- Lazy-loaded full content on expand
- SQLite column migration via `_ensure_columns()` at report generation time

### Frontend — 7 functional pages
- **Dashboard:** Top actions with PwC engagement summaries and pipeline badges. Portfolio pulse with last report date. Salesforce pipeline summary section with structured opportunity data. Default route.
- **Signals:** Two tabs (News & Regulatory / SEC Filings), three views (All / Portfolio / Discovery), category filter chips, sort dropdown (Newest, Oldest, By Source, By Industry)
- **Companies:** Search with 300ms debounce, industry/status filters, sort (A-Z, Z-A, Industry, Status, Newest), revenue-tier sizing in cards
- **Company Detail:** Eight tabs (Overview, Relationships, Profile, Intelligence, Filings, Company News, Industry News, AI Analysis). Inline Add Contact and Add Engagement forms. Tab badges show signal type breakdowns. Company News shows all match types (name + industry + semantic). Error states on tab load failure. Enrichment cards show source citations. Relationship tab shows engagement notes.
- **Upload:** Drag-and-drop for CSV, XLSX, PDF, DOCX
- **Reports:** Weekly reports with collapsed summary cards (urgency badges, opportunity summary, suggested lead, top signal) → expand for full content with "Why It Matters" financial cross-ref highlighted in blue. Summary list loads from lightweight endpoint; content lazy-loaded on expand. Brief generator with actual date ranges.
- **Outreach:** Prioritized outreach queue with urgency/status badges, PwC engagement summaries, pipeline summaries, and feedback buttons with error reporting.
- **Shared:** `markdownToHtml` + DOMPurify sanitization + `formatDate` in utils/formatters.ts. Constants (industries, sub-sectors, sizes) in utils/constants.ts. SignalSummaryBadge for type-aware counts. `@tailwindcss/typography` for prose styling. Shared type files for dashboard and outreach. Dedicated API modules for all pages. 404 route.

---

## 5. What is NOT done

### Next up: MCP-Enriched Reports Phase 3 (see MCP_ENRICHED_REPORTS_PLAN.md)

| Phase | What | Status |
|---|---|---|
| **Phase 1** | Feed all 14 MCP sources into weekly reports. Financial cross-reference. "Who Should Act" with named PwC people. | **DONE** |
| **Phase 2** | Summary + drill-down report structure. Structured fields. Collapsed → expanded UI. | **DONE** |
| **Phase 3** | Partner portfolio filtering. Partner name → company resolution via People Connector data. | Not started |

### Important but not demo-blocking
- Engagement update/delete — only create/list endpoints exist
- Pagination UI — backend supports it, frontend shows everything on one page
- Impersonation sites pass blocklist — sham domains (e.g., `royaldutchshellplc.com`) not caught. Fix: implement source allowlist (see section 6).
- No structured logging — ingestion uses print()
- Company/CIK lists: `signal_matcher.py` SHORT_NAMES is still a separate static dict from `sec_edgar.py` KNOWN_CIKS. Companies added via UI don't auto-populate SHORT_NAMES.

### Production requirements (not needed for demo)
- Authentication / authorization — every endpoint is public. No user context, no data isolation between partners.
- Database migrations — Alembic is in deps but never initialized. Weekly report columns use runtime ALTER TABLE workaround.
- Tests — zero test files anywhere.
- Celery / task queue — ingestion is CLI-only, not scheduled.
- Source credibility allowlist — current approach is a domain blocklist. Decision made to move to an allowlist of ~30-40 trusted sources (Option B), but not yet implemented.
- Docker / deployment pipeline

### Future (Phase 4 of MCP plan — post-demo, requires auth)
- Salesforce OAuth for auto-pipeline pull
- Network-aware routing (`find_people(network_scope="__caller__")`)
- Warm intro suggestions
- Meeting prep briefings
- Per-partner report framing based on engagement history

---

## 6. Architecture decisions and context

### Signal categories
`regulatory`, `macro`, `company_moves`, `trends`, `general`. Originally used "competitors" — renamed to "company_moves" because companies in the same industry are not necessarily competitors (an OEM and its Tier 1 supplier are value chain partners). SEC filings (10-K, 10-Q, 8-K, DEF 14A) categorized as "company_moves" — they are corporate disclosures, not regulatory actions. USASpending forced to "general".

### Company sizing
Revenue-anchored tiers: Mega-cap ($50B+), Large-cap ($10B-$50B), Mid-cap ($1B-$10B), Small-cap (<$1B). Stored as string values with label mapping in frontend constants.

### Source filtering direction
Current: domain blocklist (manually curated). PR wires (prnewswire.com, businesswire.com, globenewswire.com) are allowed — they carry official corporate announcements. Financial analysis sites (seekingalpha.com, benzinga.com, motleyfool.com) are also allowed. **Preferred future state:** allowlist of ~30-40 trusted source domains. Everything else dropped unless LLM scorer gives high confidence.

### Sub-sector value chain relationships
Industry matching knows that an OEM signal matched to a supplier is a "value chain" relationship, not a competitor relationship. Mapped in `VALUE_CHAIN_RELATIONSHIPS` dict in `signal_matcher.py` for all three industries. Same sub-sector = highest score (0.6), value chain partner = 0.5, unrelated sub-sectors = 0.35.

### CIK lookup — single source of truth
`sec_edgar.py` KNOWN_CIKS is the canonical company→CIK mapping. `sec_financials.py` derives its `TARGET_COMPANIES` from it (reversed). `financial_analyzer.py` imports it directly. One place to update when companies are added.

### Salesforce — advisory only
The Salesforce enricher explicitly requests only advisory, strategy, and consulting pipeline. Audit, tax, assurance, and attestation engagements are excluded from the prompt. Response is stored as raw markdown AND parsed into structured opportunity records (name, value, stage, close date, owner). Dashboard uses structured data when available, falls back to markdown truncation. Pipeline data has a 14-day staleness filter on the dashboard.

### Database
SQLite for dev. `Base.metadata.create_all()` on startup — no migration history. Weekly report structured columns added via runtime `ALTER TABLE` (in `_ensure_columns()`). Signal-company matches have a unique constraint on `(signal_id, company_id)`. To change schema: either manually `ALTER TABLE` or drop the DB and re-seed.

### Path setup
Cross-boundary imports between `backend/app/` and `ingestion/` are resolved by a single `sys.path.insert` in `backend/app/main.py` that adds the project root at startup. `seed.py` has its own path insert for the same reason (it runs standalone, not through uvicorn).

### CORS
Origins configurable via `CORS_ORIGINS` env var (comma-separated). Defaults to `http://localhost:5173,http://localhost:3000`.

---

## 7. What Ed likes and doesn't like

### Likes
- Direct, concise output. No fluff.
- Options presented, not just one answer.
- Revenue-tier sizing with the range shown in parentheses.
- Signals described by what they are (type breakdowns), not bare counts.
- "Company moves" instead of "competitors" as a category name.
- Value chain awareness in industry matching (OEM-supplier, prime-sub).
- Inline add for contacts and engagements on the company detail page.
- Allowlist direction for source credibility (over blocklist).
- Bundled PRs for related changes.
- Direct edits on this project (no AI-revised copies).
- Salesforce scoped to advisory only — no audit/tax noise.

### Doesn't like
- Bare signal counts ("19 signals") with no breakdown of what they are or how actionable they are.
- Mischaracterizing relationships — an OEM and a supplier are not competitors.
- Sham/impersonation sites passing filters (e.g., `royaldutchshellplc.com`).
- Generic talking points that ignore company context (notes, status, financials).
- Placeholder text from LLM outputs ("[current week]" instead of dates).
- Vague sizing labels ("enterprise" vs "large") with no defined criteria.
- Quick fixes over sustainable solutions.
- Audit/tax data cluttering advisory-focused views.

---

## 8. How to run locally

**Backend:**
```bash
cd backend
../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```
On first startup, the backend will auto-categorize any signals with NULL `news_category` and rename legacy "competitors" to "company_moves".

**Frontend:**
```bash
cd frontend
node_modules\.bin\vite.cmd
```
Node is managed via fnm. The Vite dev server proxies `/api` to `localhost:8000`.

- Backend: http://localhost:8000 (health check at /health)
- Frontend: http://localhost:5173

**Ingestion (manual, one source at a time):**
```bash
cd backend
../.venv/Scripts/python -m ingestion.run --source news
../.venv/Scripts/python -m ingestion.run --source sec_edgar
../.venv/Scripts/python -m ingestion.run --source federal_register
../.venv/Scripts/python -m ingestion.run --source gdelt
../.venv/Scripts/python -m ingestion.run --source sam_gov
../.venv/Scripts/python -m ingestion.run --source usaspending
../.venv/Scripts/python -m ingestion.run --source event_registry
```

**MCP enrichment:**
```bash
cd backend
../.venv/Scripts/python -m ingestion.enrich                    # List what needs populating
../.venv/Scripts/python -m ingestion.enrich --mcp capiq        # Run one enricher
../.venv/Scripts/python -m ingestion.enrich --mcp all          # Run all enrichers
```

**Seed database:**
```bash
cd backend
../.venv/Scripts/python seed.py
```

---

## 9. Git workflow

- `main` is stable — never commit directly.
- Feature branches: `feature/<description>` or dated like `09-25-FE-Signals-Matching`.
- Both contributors should review PRs when possible.
- Two people use Claude Code on this repo. **Start every session by asking who is working and what changed since last time.**

---

## 10. Known bugs

| Bug | File | Impact | Status |
|---|---|---|---|
| Impersonation sites pass blocklist | `relevance_scorer.py` | `royaldutchshellplc.com` etc. not caught. Fix: implement allowlist (see section 6). | Open |
| Engagement update/delete missing | `engagements.py` | Only create/list — no PATCH/DELETE endpoints | Open — low priority |
| No pagination in frontend | Multiple pages | Backend supports it, frontend shows everything | Open — cosmetic |
| SHORT_NAMES static dict | `signal_matcher.py` | Companies added via UI don't auto-populate SHORT_NAMES for name matching | Open — architectural |

### Previously reported bugs (now resolved)

| Bug | Resolution |
|---|---|
| `run.py` signal IDs are None before commit | Fixed — `session.flush()` populates IDs before collection |
| `sec_financials.py` ImportError on `TARGET_COMPANIES` | Fixed — `TARGET_COMPANIES` now derived from `sec_edgar.py` KNOWN_CIKS (single source of truth) |
| `anthropic` missing from requirements.txt | Fixed — `anthropic>=0.52.0` present |
| `dangerouslySetInnerHTML` unsanitized (XSS) | Fixed — `markdownToHtml()` runs all content through `DOMPurify.sanitize()` |
| `sys.path.insert` hacks in 4 files | Fixed — consolidated to single path setup in `main.py` |
| `@tailwindcss/typography` not installed | Fixed — installed and wired via `@plugin` in `index.css` |
| `Source` model orphaned | Fixed — deleted `source.py` and removed from exports |
| `httpx2` nonstandard import in LLM client | Fixed — replaced with standard `httpx`, SSL verification restored |
| `delete_company` leaves orphan rows | Fixed — cascade delete now cleans up matches, outreach actions, reports, analyses, profiles, enrichments |
| N+1 query storm in outreach ranker (~800 queries) | Fixed — batch prefetch of OutreachAction and Contact records (~6 queries total) |
| SEC filings all categorized as "regulatory" | Fixed — 10-K/10-Q/8-K/DEF 14A now categorized as "company_moves" |
| PR wires blocked (prnewswire, businesswire, globenewswire) | Fixed — removed from blocklist, official corporate announcements now pass through |
| Frontend sends unused `filing_ids` param | Fixed — removed from `triggerFinancialAnalysis` |
| Profile generation response missing fields | Fixed — `POST /profile/generate` now returns `financial_summary` and `news_summary` |
| Energy sector undercovered in ingestion | Fixed — GDELT/Event Registry use 30 keywords (all 3 verticals), Federal Register includes FERC/DOE/NRC |
| CIK lookup duplicated in 3 files | Fixed — `sec_financials.py` and `financial_analyzer.py` now import from `sec_edgar.py` KNOWN_CIKS |
| `Signal.importance_score` column always NULL | Fixed — removed from model, schema, and frontend type |
| No unique constraint on signal-company matches | Fixed — added `UniqueConstraint("signal_id", "company_id")` |
| Industry slug normalization too narrow (4 entries) | Fixed — expanded to 16 entries covering energy, utilities, oil & gas, and common abbreviations |
| SSL verification disabled in LLM client | Fixed — `verify=False` removed |
| CORS hardcoded to localhost | Fixed — configurable via `CORS_ORIGINS` env var |
| Stale "competitors" in signals API docs | Fixed — updated to "company_moves" |
| Signals API duplicated filter logic (3 endpoints) | Fixed — extracted `_apply_signal_filters()` shared helper |
| Dashboard/outreach pages bypass API layer | Fixed — dedicated `api/dashboard.ts` and `api/outreach.ts` modules created |
| Dashboard/outreach types defined locally | Fixed — moved to `types/dashboard.ts` and `types/outreach.ts` |
| CompanyDetailPage swallows intelligence errors | Fixed — added `intelError` state with error messages on tabs |
| Outreach feedback errors silently swallowed | Fixed — added `feedbackError` state with error banner |
| Company News tab dropped industry/semantic matches | Fixed — removed `match_type === 'name'` filter |
| `datetime.utcnow()` deprecated in base_enricher | Fixed — replaced with `datetime.now(timezone.utc)` |
| Dedup hash included raw `published_at` (breaks on None) | Fixed — formatted as date string, empty string when None |
| Classifier tie always resolves to automotive | Fixed — density-based tie resolution (hits / total keywords) |
| Overflow candidates bypass LLM filter entirely | Fixed — filtered to `match_score >= 0.5` |
| `_compute_match_score` private import in seed.py | Fixed — renamed to public `compute_match_score` |
| Reports list loads full content for all reports | Fixed — list uses `/reports/weekly/summary` (no content), detail lazy-loaded on expand |
| Salesforce enricher returns audit/tax data | Fixed — prompt now explicitly requests advisory/strategy only, excludes audit/tax/assurance |
| Salesforce `response_summary` never populated | Fixed — enricher now parses opportunities into structured JSON (name, value, stage, close date, owner) |
| Dashboard pipeline summary has no staleness filter | Fixed — 14-day max age filter applied, structured data displayed when available |
| Salesforce `pipeline_summary` computed but never displayed | Fixed — passed through outreach ranker to frontend, rendered on OutreachPage |
| Report detail endpoint missing `company_id` field | Fixed — added to response dict |
| Unused `selectinload` import in outreach ranker | Fixed — removed |
