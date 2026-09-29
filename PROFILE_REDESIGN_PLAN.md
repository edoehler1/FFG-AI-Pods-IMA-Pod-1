# Plan: Redesign Company Profile + Separate Financial Analysis

**Status:** In progress. `financial_analysis.py` model created, everything else pending.
**Branch:** `feature/mcp-integration-and-dashboard`

---

## Context

The current company profile is a wall of unformatted text that dumps raw SEC XBRL numbers and recent news into a single LLM prompt. It needs to be:
1. Readable and partner-ready
2. An annual baseline (full fiscal year, not last week's news)
3. Benchmarked against industry peers
4. Connected to the real S& taxonomy and real PwC contacts

The new design splits into two pieces:
- **Financial Analysis** — separate per-company document comparing last two 10-Ks + 10-Q quarterly trends, benchmarked against industry peers
- **Company Profile** — clean annual baseline that references the financial analysis, combines 12 months of news, maps to S& taxonomy

Weekly reports compare new signals against THIS baseline.

---

## Part 1: Industry Benchmark Model

**Build FIRST** — this is the yardstick for all financial analyses.

### New model: `backend/app/models/financial_analysis.py` (ALREADY CREATED)

Contains both `FinancialAnalysis` and `IndustryBenchmark` models.

### New service: `backend/app/services/benchmark_builder.py`

For each of the 3 industries (automotive, aerospace_defense, energy):
1. Pull SEC XBRL financials for EVERY company in that sector using `ingestion/sources/sec_financials.py`
2. Compute metrics: revenue, operating margin, gross margin, revenue growth YoY, R&D as % revenue, debt/equity, capex as % revenue
3. Store median, min, max, avg for each metric + company rankings
4. Store as JSON in `IndustryBenchmark` table

CIK numbers are in `ingestion/sources/sec_edgar.py` → `KNOWN_CIKS` dict. Companies per industry:
- **Automotive:** Ford, GM, Tesla, Rivian, Stellantis, Aptiv, Magna (+ Bosch via CapIQ if available)
- **A&D:** Lockheed Martin, Boeing, RTX, Northrop Grumman, General Dynamics, L3Harris
- **Energy:** ExxonMobil, Chevron, Shell, NextEra, Duke Energy, Enbridge

### API: `GET /api/benchmarks/{industry}`

---

## Part 2: Financial Analysis Agent (per company)

### New service: `backend/app/services/financial_analysis_agent.py`

For each company:
1. Pull last two years of SEC XBRL data via `sec_financials.py` → `fetch_company_financials()`
2. Pull CapIQ enrichment from `mcp_enrichments` (if stored)
3. Pull earnings call enrichment from `mcp_enrichments` (if stored)
4. Load the industry benchmark for this company's sector
5. Send to LLM with this prompt structure:

```markdown
# {Company} — Financial Analysis (FY2025 vs FY2024)

## Revenue & Growth
FY numbers, YoY comparison, quarterly trends from 10-Qs.
"vs industry median of X%" using the benchmark.

## Profitability
Operating margin, gross margin, SG&A trends.
"Ranks Nth of N companies in the sector."

## Balance Sheet
Debt, capex, assets. Deleveraging or leveraging? Why?

## Peer Benchmark
Compare to 2-3 closest peers from the benchmark data.
Where does this company outperform? Underperform?

## Key Takeaway
One paragraph: what the numbers say about where this company is headed.
```

Store in `FinancialAnalysis` table with:
- `content` — the LLM-generated markdown
- `key_metrics` — JSON of raw numbers (revenue, margins, etc.)
- `peer_comparison` — JSON of the benchmark comparison

### API: `GET /api/companies/{id}/financial-analysis`

---

## Part 3: Redesigned Company Profile

### Rewrite `backend/app/services/profile_builder.py`

**Data inputs:**
- Financial analysis from Part 2 (referenced, not inlined)
- Full 12 months of news (change from `limit(15)` to 12-month window, up to 30 signals)
- Full MCP enrichment context via `build_enrichment_context()` — already wired
- Real S& taxonomy from `capability_taxonomy.json` — already replaced
- Real client contacts from `contacts` table — already populated
- PwC engagement history from People Connector enrichment — already stored
- Industry benchmark from Part 1

**New LLM prompt produces:**

```markdown
# {Company} — Company Profile

## At a Glance
- What they do (1 sentence)
- Revenue: $X (FY) | +/-% YoY
- Industry position: vs median, rank
- Client status: active/target/past
- GRP: Name (practice, office)
- S& lead: Name (practice, office) — if any S& engagements exist

## The Story
THE most important paragraph. Connect financials → news → PwC relationship → opportunity.
This is what the partner reads first.

## Key Developments (Past 12 Months)
8-10 most significant events, chronological. Date + what happened + why it matters.

## Financial Position
2-3 sentence narrative referencing the financial analysis. Not raw numbers.
"Revenue flat at $20B while margins compressed due to..."

## S& Opportunity
Specific capability from the taxonomy. Why now? Concrete engagement scope.
Taxonomy tag: [exact capability name from taxonomy]

## Who Should Act
- GRP: Name — email — relationship owner
- S& Lead: Name — email — led [engagement], knows the operations
- Client contact: Name — department — email
```

**Key changes:**
- Profile cap expanded from 15 signals to 30 (12-month window)
- Financial data is narrative, not raw XBRL dump
- "The Story" is the lead section after At a Glance
- S& opportunity maps to real taxonomy
- "Who Should Act" uses People Connector structured data (GRP, engagement staff)
- MCP enrichment context capped at 4000 chars to manage token budget

---

## Part 4: Frontend

### Rewrite `frontend/src/components/companies/CompanyProfile.tsx`

Render with styled sections instead of single markdown blob:
- **At a Glance** — card at top with key facts
- **The Story** — prominent section, larger text
- **Key Developments** — timeline-style list
- **Financial Position** — with link/expand to full financial analysis
- **S& Opportunity** — with taxonomy badge
- **Who Should Act** — contact cards with emails

### Add financial analysis view
Either a sub-tab within Profile or expandable section. Shows the full financial analysis markdown.

---

## Key Reference Files

| File | What | Status |
|---|---|---|
| `backend/app/models/financial_analysis.py` | FinancialAnalysis + IndustryBenchmark models | CREATED |
| `backend/app/services/benchmark_builder.py` | Industry benchmark computation | TO BUILD |
| `backend/app/services/financial_analysis_agent.py` | Per-company financial analysis | TO BUILD |
| `backend/app/services/profile_builder.py` | Company profile generation | TO REWRITE |
| `backend/app/api/companies.py` | Add benchmark + financial analysis endpoints | TO MODIFY |
| `frontend/src/components/companies/CompanyProfile.tsx` | Profile display | TO REWRITE |
| `ingestion/sources/sec_financials.py` | SEC XBRL data fetcher (existing) | REUSE |
| `ingestion/sources/sec_edgar.py` | KNOWN_CIKS dict (existing) | REUSE |
| `backend/app/services/enrichment_reader.py` | MCP enrichment reader (existing) | REUSE |
| `backend/app/services/taxonomy.py` | S& taxonomy loader (existing) | REUSE |
| `backend/seed_data/capability_taxonomy.json` | Real S& taxonomy (existing) | REUSE |

## Verification

1. Generate industry benchmarks for all 3 sectors — verify median/ranking data
2. Generate financial analysis for Aptiv — shows FY2025 vs FY2024 with peer benchmark
3. Generate profile for Aptiv — clean "At a Glance" + "The Story" format
4. Profile references financial analysis narrative, not raw numbers
5. S& opportunity maps to real taxonomy capability
6. "Who Should Act" shows real PwC people from People Connector
7. Frontend renders styled sections, not wall of text

## How to Run

```bash
# Backend
cd backend && python -m uvicorn app.main:app --reload --port 8000

# Generate benchmarks (run once)
# POST /api/benchmarks/generate or via script

# Generate financial analysis for a company
# POST /api/companies/{id}/financial-analysis/generate

# Generate profile for a company
# Click "Refresh Profile" on company detail page
```
