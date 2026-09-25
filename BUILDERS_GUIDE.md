# Sales Intelligence Platform — Builder's Guide

**Last updated:** 2026-09-25
**Contributors:** Gabriel Solis, Ethan Doehler (IMA AI Pod)
**Status:** Demo-stage MVP. Core loop functional. Not production-ready.

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
| Backend | Python 3.12 / FastAPI / SQLAlchemy | ~25 real API endpoints |
| Frontend | TypeScript / React 19 / Vite 8 / Tailwind CSS v4 | 5 pages, all wired to real backend |
| Database | SQLite (dev) | PostgreSQL planned for prod. No Alembic migrations — `create_all()` on startup. |
| LLM | Claude API (Anthropic) via configurable gateway | Dual-mode client: OpenAI-compatible gateway + native Anthropic SDK |
| Ingestion | Python CLI runner | 7 live data sources. No Celery/task queue — synchronous only. |
| Infrastructure | Local dev only | No Docker, no deployment pipeline |

---

## 3. File structure (as of 09-25)

```
FFG-AI-Pods-IMA-Pod-1/
├── backend/
│   ├── app/
│   │   ├── main.py                         # FastAPI app, CORS, startup signal categorization
│   │   ├── config.py                       # Settings from .env (DB URL, API keys, model name)
│   │   ├── database.py                     # SQLAlchemy engine, SessionLocal, Base
│   │   ├── api/
│   │   │   ├── router.py                   # Mounts all sub-routers under /api
│   │   │   ├── companies.py                # CRUD + intelligence + analysis + profiles + sort/filter
│   │   │   ├── contacts.py                 # Full CRUD (scoped to company)
│   │   │   ├── engagements.py              # List + Create (no update/delete yet)
│   │   │   ├── signals.py                  # Signal browsing: all, portfolio, discovery + categorize
│   │   │   ├── reports.py                  # Weekly reports + on-demand briefs with date ranges
│   │   │   ├── profiles.py                 # Company profile CRUD + generation
│   │   │   └── upload.py                   # CSV/XLSX/PDF/DOCX bulk import
│   │   ├── models/
│   │   │   ├── company.py, contact.py, engagement.py
│   │   │   ├── signal.py                   # Includes news_category column
│   │   │   ├── signal_company.py           # Match junction (score, type, reason, talking_points)
│   │   │   ├── company_analysis.py, company_profile.py, weekly_report.py
│   │   │   └── source.py                   # ORPHANED — never queried or written to
│   │   ├── schemas/                        # Pydantic schemas (company, contact, engagement, signal)
│   │   └── services/
│   │       ├── signal_matcher.py           # 4-stage pipeline: name→industry→LLM→talking points
│   │       ├── signal_categorizer.py       # LLM + keyword categorization
│   │       ├── signal_summarizer.py        # Type/category breakdown utility
│   │       ├── relevance_scorer.py         # Domain blocklist + Claude quality scoring
│   │       ├── onboarding.py               # Auto-pipeline on company creation
│   │       ├── company_analyzer.py         # Intelligence aggregation + LLM analysis
│   │       ├── financial_analyzer.py       # SEC XBRL data + LLM analysis
│   │       ├── profile_builder.py          # Comprehensive company profile generation
│   │       ├── weekly_report_agent.py      # Per-company weekly intelligence
│   │       ├── report_generator.py         # Portfolio-wide signal briefs
│   │       ├── taxonomy.py                 # S& capability taxonomy loader
│   │       ├── upload_parser.py            # Multi-format parser (CSV/XLSX/PDF/DOCX)
│   │       └── llm_client.py              # Dual-mode Claude client
│   ├── seed.py                             # DB seeder (companies, contacts, matching)
│   ├── seed_data/                          # capability_taxonomy.json, sample CSVs
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                         # Routing with 404 catch-all
│   │   ├── api/                            # Axios clients: companies, contacts, engagements, signals, reports, upload
│   │   ├── components/
│   │   │   ├── common/                     # FilterPanel, FileUploader, SignalSummaryBadge
│   │   │   ├── companies/                  # Card, List, Form, Analysis, Profile, Filings, News
│   │   │   ├── contacts/                   # ContactForm (inline add modal)
│   │   │   ├── engagements/                # EngagementForm (inline add modal)
│   │   │   ├── signals/                    # SignalCard (with relevance gradient), SignalList, FilingsView
│   │   │   └── layout/                     # Header, Sidebar
│   │   ├── hooks/                          # useCompanies, useCompany, useSignals, useDebouncedValue
│   │   ├── pages/                          # SignalsPage, CompaniesPage, CompanyDetailPage, ReportsPage, UploadPage
│   │   ├── types/                          # company, contact, engagement, signal
│   │   └── utils/                          # constants.ts (industries, sub-sectors, sizes), formatters.ts
│   ├── package.json, vite.config.ts
│   └── index.html                          # Title: "Sales Intelligence Platform"
├── ingestion/
│   ├── run.py                              # CLI: python -m ingestion.run <source>
│   ├── config.py                           # API keys, industry keyword lists
│   ├── sources/                            # 7 source clients (news_rss, sec_edgar, federal_register, gdelt, sam_gov, usaspending, event_registry)
│   └── processing/                         # classifier.py (keyword), deduplication.py (SHA-256)
├── data/signals.db                         # SQLite database
├── .env                                    # API keys and config (never committed)
├── Sales_Intelligence_Platform_Project_Plan.md   # Full product spec
├── Technical_Reference_File_Structure.md         # Original file tree by phase (partially outdated)
├── CLAUDE.md                               # Coding conventions, git workflow
└── BUILDERS_GUIDE.md                       # This file
```

---

## 4. What is done

### Ingestion — 7 live data sources, all hitting real APIs
- Google News RSS (company-specific + 25 industry queries + 3 supplemental defense/space feeds)
- SEC EDGAR filings (10-K, 10-Q, 8-K, DEF 14A with per-type caps)
- Federal Register (NHTSA, FAA, DoD, EPA)
- GDELT news
- SAM.gov contracts (requires API key)
- USASpending awards
- Event Registry (requires API key)
- Keyword-based industry/sub-sector/type classification
- SHA-256 title dedup
- Source credibility domain blocklist at ingestion time

### Backend — ~25 API endpoints
- **Companies:** Full CRUD, sort/filter (name, industry, status, created_at), search
- **Contacts:** Full CRUD scoped to company
- **Engagements:** List + Create (no update/delete)
- **Signals:** List with filters (industry, sub-sector, type, category, source), portfolio view (matched to active/past clients), discovery view (unmatched)
- **Reports:** Weekly per-company reports (LLM-generated, opportunity detection), on-demand portfolio briefs with actual date ranges
- **Profiles:** Company profile generation via LLM
- **Upload:** CSV, XLSX, PDF, DOCX with flexible header aliasing
- **On startup:** auto-categorizes any signals with NULL news_category, renames legacy "competitors" category to "company_moves"

### Signal matching pipeline (the core intelligence)
1. **Name match** — regex word-boundary search against `SHORT_NAMES` dict (27 companies). Ambiguous names (Ford, Shell, GM, Magna, AES) require industry + business context words to score above 0.5 threshold. Non-SEC signals filtered through consumer content blocklist and domain blocklist.
2. **Industry match** — same-industry signals matched to companies with sub-sector relationship awareness. Value chain relationships mapped (OEM-supplier, prime-subcontractor, upstream-midstream, etc.) — not everyone in the same industry is a competitor.
3. **LLM relevance filter** — Claude scores industry-match candidates 0.0-1.0 using 500-char body snippets. Threshold: 0.4.
4. **Talking points** — Claude generates 3-4 bullets per match incorporating company context (client status, notes, size, geography, S& capabilities). Framing adapted to relationship status: target = pitch, active = deepen, past = re-engage. Template fallback when LLM unavailable.

### Frontend — 5 functional pages
- **Signals:** Two tabs (News & Regulatory / SEC Filings), three views (All / Portfolio / Discovery), category filter chips, sort dropdown (Newest, Oldest, By Source, By Industry)
- **Companies:** Search with 300ms debounce, industry/status filters, sort (A-Z, Z-A, Industry, Status, Newest), revenue-tier sizing in cards
- **Company Detail:** Six tabs (Overview, Profile, Filings, Company News, Industry News, AI Analysis). Inline Add Contact and Add Engagement forms. Tab badges show signal type breakdowns (not bare counts). Company News sorted by relevance with colored gradient borders.
- **Upload:** Drag-and-drop for CSV, XLSX, PDF, DOCX
- **Reports:** Weekly reports with expand/collapse and opportunity badges. Brief generator with actual date ranges.
- **Shared:** `markdownToHtml` + `formatDate` in utils/formatters.ts. Constants (industries, sub-sectors, sizes) in utils/constants.ts. SignalSummaryBadge for type-aware counts. 404 route.

---

## 5. What is NOT done

### Critical for production (not needed for demo)
- **Authentication / authorization** — every endpoint is public. No user context, no data isolation between partners.
- **Database migrations** — Alembic is in deps but never initialized. Schema changes require manual `ALTER TABLE` or drop + recreate.
- **Tests** — zero test files anywhere.
- **Celery / task queue** — ingestion is CLI-only, not scheduled.
- **Source credibility allowlist** — current approach is a domain blocklist. Decision made to move to an allowlist of ~30-40 trusted sources (Option B), but not yet implemented. Impersonation sites (e.g., `royaldutchshellplc.com`) still pass through.

### Important but not demo-blocking
- **Engagement update/delete** — only create/list endpoints exist
- **Pagination UI** — backend supports it, frontend shows everything on one page
- **`sec_financials.py` broken import** — `TARGET_COMPANIES` reference doesn't exist, crashes financial analyzer
- **`run.py` signal ID bug** — `signal.id` captured before commit (all None), post-ingestion matching silently skips
- **`anthropic` missing from requirements.txt** — must be manually installed
- **`@tailwindcss/typography` not installed** — prose classes on AI content render unstyled
- **`dangerouslySetInnerHTML` without sanitization** — XSS risk in 4 frontend components
- **No structured logging** — ingestion uses print()
- **`Source` model orphaned** — table created but never used

---

## 6. Architecture decisions and context

### Signal categories
`regulatory`, `macro`, `company_moves`, `trends`, `general`. Originally used "competitors" — renamed to "company_moves" because companies in the same industry are not necessarily competitors (an OEM and its Tier 1 supplier are value chain partners). SEC filings forced to "regulatory". USASpending forced to "general".

### Company sizing
Revenue-anchored tiers: Mega-cap ($50B+), Large-cap ($10B-$50B), Mid-cap ($1B-$10B), Small-cap (<$1B). Stored as string values with label mapping in frontend constants.

### Source filtering direction
Current: domain blocklist (manually curated, ~30 domains). **Preferred future state:** allowlist of ~30-40 trusted source domains (Reuters, WSJ, Bloomberg, SEC.gov, defensenews.com, etc.). Everything else dropped unless LLM scorer gives high confidence. This eliminates the whack-a-mole problem entirely.

### Sub-sector value chain relationships
Industry matching knows that an OEM signal matched to a supplier is a "value chain" relationship, not a competitor relationship. Mapped in `VALUE_CHAIN_RELATIONSHIPS` dict in `signal_matcher.py` for all three industries. Same sub-sector = highest score (0.6), value chain partner = 0.5, unrelated sub-sectors = 0.35.

### Database
SQLite for dev. `Base.metadata.create_all()` on startup — no migration history. To change schema: either manually `ALTER TABLE` or drop the DB and re-seed.

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

### Doesn't like
- Bare signal counts ("19 signals") with no breakdown of what they are or how actionable they are.
- Mischaracterizing relationships — an OEM and a supplier are not competitors.
- Sham/impersonation sites passing filters (e.g., `royaldutchshellplc.com`).
- Generic talking points that ignore company context (notes, status, financials).
- Placeholder text from LLM outputs ("[current week]" instead of dates).
- Vague sizing labels ("enterprise" vs "large") with no defined criteria.
- Quick fixes over sustainable solutions.

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
../.venv/Scripts/python -m ingestion.run news
../.venv/Scripts/python -m ingestion.run sec_edgar
../.venv/Scripts/python -m ingestion.run federal_register
../.venv/Scripts/python -m ingestion.run gdelt
../.venv/Scripts/python -m ingestion.run sam_gov
../.venv/Scripts/python -m ingestion.run usaspending
../.venv/Scripts/python -m ingestion.run event_registry
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

| Bug | File | Impact |
|---|---|---|
| `sec_financials.py` ImportError on `TARGET_COMPANIES` | `ingestion/sources/sec_financials.py:7` | Crashes financial analyzer and profile builder |
| `run.py` signal IDs are None before commit | `ingestion/run.py:105` | Post-ingestion company matching silently does nothing |
| `anthropic` not in requirements.txt | `backend/requirements.txt` | LLM client fails unless manually installed |
| `sys.path.insert` hacks | `onboarding.py`, `financial_analyzer.py`, `profile_builder.py` | Breaks under different working directories |
| `dangerouslySetInnerHTML` unsanitized | 4 frontend components | XSS risk if signal content contains scripts |
| Impersonation sites pass blocklist | `relevance_scorer.py` | `royaldutchshellplc.com` etc. not caught. Fix: implement allowlist (see section 6). |
