# Builder's Guide

*Living document — updated as the project evolves. Last updated: 2026-09-23 (Phase 1 backend + ingestion + frontend built).*

---

## 1. Feasibility Assessment

### What's realistic for two people + Claude Code

The project plan describes enterprise-grade software (~170 files, 5 phases, 16-18 weeks). That plan assumes a full engineering team. Here's what's **actually buildable** by two associates leaning heavily on Claude Code:

| Aspect | Realistic (v0.1) | Aspirational (full plan) |
|---|---|---|
| Signal sources | 2-3 free APIs (NewsAPI, SEC EDGAR, Federal Register) | 7+ sources including licensed data (PitchBook, GovWin) |
| Signal processing | Basic dedup + LLM classification | Full entity resolution + importance scoring pipeline |
| Frontend | Functional dashboard showing signals + basic filtering | Full multi-view app with outreach queue, upload center, settings |
| Database | PostgreSQL with basic schema | PostgreSQL + vector DB + object storage |
| Auth | Simple login (username/password or magic link) | Azure AD SSO with row-level security |
| LLM integration | Claude API for signal matching + talking point generation | Full recommendation engine with feedback loops and personalization |
| Hosting | Free tier (Railway, Render, or Vercel) for demo | PwC Azure with Terraform, CI/CD, compliance |
| Users | Demo with sample data, maybe 1-2 real partners/directors | Multi-tenant with data isolation |

### What makes this project feasible

- **Claude Code generates most of the code.** Scaffolding, API routes, React components, database models — Claude handles the boilerplate. You focus on decisions and testing.
- **PwC covers costs.** Claude API, hosting, and data sources aren't blockers.
- **The pod has senior people.** Dirk, Ryan, and senior managers can unlock data access, validate the capability taxonomy, and navigate compliance.

### What could block us

| Blocker | Severity | Mitigation |
|---|---|---|
| No access to real partner data for testing | High | Build with synthetic/sample data first. Design for real data later. |
| PwC compliance won't approve external hosting | Medium | Start on free tier for demo. Move to Azure when pod secures IT approval. |
| Data source APIs require enterprise licenses we can't get | Medium | Start with free sources. The pod's senior members can pursue licensing. |
| Scope creep — trying to build the full plan at once | High | Stick to the phased milestones below. Ship v0.1 before adding features. |

---

## 2. Data Sources

### Free / Low-Cost (start here)

| Source | What it gives us | API | Cost | Notes |
|---|---|---|---|---|
| **NewsAPI** | News articles from major outlets | REST API | Free tier: 100 req/day, 1-month-old articles. Dev plan: $449/mo for real-time. | Good for MVP. Free tier has delay limitations. |
| **GDELT** | Global news events, tone analysis | REST API (open) | Free | Massive dataset, no auth required. Good alternative to NewsAPI. |
| **SEC EDGAR** | 10-K, 10-Q, 8-K filings, insider transactions | REST API | Free | Full-text search API. Excellent for earnings and leadership signals. |
| **Federal Register** | Proposed and final rules, executive orders | REST API | Free | Key for regulatory signals in auto and A&D. |
| **SAM.gov** | Government contract opportunities and awards | REST API | Free (requires registration) | Core for A&D government contract signals. |
| **USASpending.gov** | Federal spending data | REST API | Free | Supplements SAM.gov for contract analysis. |
| **Event Registry** | News aggregation with entity recognition | REST API | Free tier: 2,000 queries/mo | Better entity resolution than raw NewsAPI. |

### Paid / Licensed (needs PwC procurement or pod help)

| Source | What it gives us | Cost | Who can help |
|---|---|---|---|
| **PitchBook / Capital IQ** | M&A deals, company financials, investor data | Enterprise license ($$$) | Check if PwC already has access — ask Dirk or Ryan |
| **GovWin (Deltek)** | Government contract intelligence, pipeline data | Enterprise license | Check existing PwC subscriptions |
| **LinkedIn Sales Navigator** | Contact data, job changes, company updates | ~$100/mo per seat | Personal accounts work for MVP |
| **Automotive News / Defense News** | Industry-specific trade press | Subscription | Pod budget or PwC library access |

### Data we need to create ourselves

| Data | Who creates it | Format |
|---|---|---|
| **S& capability taxonomy** | Dirk or senior managers validate | JSON tree structure |
| **Sample company profiles** | Gabriel + Ethan (based on public info) | CSV or direct DB entry |
| **Sample contacts and relationships** | Gabriel + Ethan (synthetic data) | CSV |
| **Sample proposals** | Not needed for v0.1 — mock data is fine | — |

---

## 3. Task Division

### What Claude Code does

- Scaffolds the FastAPI backend (models, schemas, routes, tests)
- Scaffolds the React frontend (components, pages, hooks, API clients)
- Writes the ingestion pipeline (API clients for each data source)
- Writes database migrations
- Implements the LLM matching logic (signal-to-company, signal-to-capability)
- Generates talking point prompts
- Sets up Docker configurations
- Writes tests
- Helps debug issues
- Reviews PRs (when asked)

### What Gabriel and Ethan do

- **Architecture decisions** — Choose between options Claude presents (e.g., which vector DB, which hosting)
- **API key setup** — Register for NewsAPI, SEC EDGAR, SAM.gov, etc. Store keys in `.env`
- **Data entry** — Create the sample company profiles, contacts, and capability taxonomy
- **Testing** — Run the app, use it, report what's broken or confusing
- **Design input** — What should the dashboard look like? What's the most important view?
- **Git workflow** — Create branches, open PRs, review each other's work
- **Present to pod** — Demo progress, explain architecture, state what's needed

### What the pod needs to provide (when the time comes)

- **Capability taxonomy validation** — Dirk or a senior manager confirms the S& offering structure
- **Data source access** — Does PwC have PitchBook? Capital IQ? GovWin? Who do we ask?
- **Compliance guidance** — When we're ready to move beyond demo, what does IT need?
- **Domain expertise** — What signals actually matter to partners? What's noise?
- **User testing** — Eventually, 1-2 partners/directors try the tool and give feedback

---

## 4. Phased Build Plan

### Phase 0: Foundation (done)
**Goal:** Repo setup, conventions, and shared understanding.
- [x] Project plan and technical reference in repo
- [x] CLAUDE.md with conventions
- [x] .gitignore
- [x] Builder's guide (this document)
- [x] Basic directory structure (backend/, frontend/, ingestion/, infra/)
- [ ] Set up branch protection on main (GitHub settings)

### Phase 1: Signal Ingestion MVP (in progress)
**Goal:** Pull real signals from 2-3 sources, store them, display them.
- [x] SQLite database schema for signals and sources (auto-created via SQLAlchemy)
- [x] FastAPI backend with `/api/signals` endpoint (GET list with filters, GET by id)
- [x] GDELT ingestion client (written, blocked by corporate network — works outside proxy)
- [x] SEC EDGAR ingestion client (written, blocked by SEC rate limiting from corporate network)
- [x] Federal Register ingestion client (working — 20 real signals ingested)
- [x] Basic deduplication (hash-based)
- [x] Keyword-based classification (industry, signal type) — LLM classification deferred to Phase 3
- [x] React + TypeScript + Tailwind frontend: signal list with industry/type filters
- [ ] Docker Compose for local dev (deferred — SQLite works for now)

### Phase 2: Company and Relationship Layer
**Goal:** Partners can manage their portfolio in the tool.
- [ ] Company and contact database models
- [ ] CRUD API for companies, contacts
- [ ] CSV upload and parsing
- [ ] Company detail view in frontend
- [ ] Manual signal-to-company linking in the UI

### Phase 3: Recommendation Engine
**Goal:** Claude API matches signals to companies and generates talking points.
- [ ] Claude API integration (signal matching prompts)
- [ ] S& capability taxonomy (JSON, loaded at startup)
- [ ] Recommendation generation pipeline
- [ ] Outreach queue view in frontend
- [ ] Urgency scoring

### Phase 4+: Personalization, Feedback, Scale
**Goal:** The pod decides what's next based on partner feedback.
- Feedback loop on recommendations
- Per-user preference tuning
- Additional data sources
- Second industry vertical
- Production hosting on Azure

---

## 5. Open Questions and Blockers

*Track items here as they come up. Resolve them before they block progress.*

| # | Question | Status | Owner | Resolution |
|---|---|---|---|---|
| 1 | Does PwC have existing PitchBook or Capital IQ licenses? | Open | Ask Dirk/Ryan | — |
| 2 | What hosting is acceptable for a demo? (free tier OK or must be Azure?) | Open | Ask Ryan | — |
| 3 | Is the capability taxonomy in the project plan accurate? Who validates? | Open | Dirk | — |
| 4 | What Claude API plan does PwC have? Any restrictions on data sent? | Open | Ask Ryan | — |
| 5 | Should we start with auto or A&D as the pilot industry? | Open | Gabriel + Ethan decide | — |

---

## 6. GitHub Collaboration Workflow

Both Gabriel and Ethan work on this repo. Here's how to avoid stepping on each other:

1. **Never commit directly to main.** Always create a feature branch first.
2. **Branch naming:** `feature/signal-ingestion`, `fix/dashboard-filter`, etc.
3. **Pull requests:** Open a PR when your branch is ready. The other person reviews (even a quick look is fine).
4. **Divide work by module.** If Gabriel is building the ingestion pipeline, Ethan works on the frontend (or vice versa). Parallel work on different modules avoids merge conflicts.
5. **Sync often.** Pull from main before starting new work. Push your branches regularly.
6. **Claude Code sessions:** Start each session by telling Claude who you are and what changed since last time. This keeps the AI context accurate.

### Quick Git Reference

```bash
# Start new work
git checkout main
git pull origin main
git checkout -b feature/my-feature

# Save progress
git add <files>
git commit -m "Add signal ingestion for NewsAPI"
git push origin feature/my-feature

# Open a PR on GitHub, then merge after review

# After merging, clean up
git checkout main
git pull origin main
git branch -d feature/my-feature
```
