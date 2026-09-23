# Sales Intelligence Platform — Project Plan

**Purpose:** An industry-signal and relationship intelligence tool that helps Strategy& directors and partners identify, prioritize, and act on sales opportunities in automotive and A&D.

**Core thesis:** Partners already track market signals, client relationships, and S& capabilities — but in their heads, in email, and in scattered files. This tool connects those three streams, surfaces the highest-value outreach opportunities, and tells each partner what to say and when to say it.

---

## 1. What the tool does

The platform answers five questions for each partner, every day:

1. **What just happened?** — Market signals relevant to their portfolio (news, regulation, executive moves, earnings, government action).
2. **Who does it affect?** — Which companies and contacts in their network are impacted.
3. **What should I pitch?** — Which S& capabilities align to the signal and the company's strategic context.
4. **When should I reach out?** — Urgency scoring based on signal recency, relationship warmth, and sales cycle timing.
5. **What do I say?** — Draft talking points that connect the signal, the relationship history, and the S& value proposition.

---

## 2. Data architecture

### 2.1 Two-tier data model

| Tier | Contents | Source | Visibility |
|---|---|---|---|
| **Base layer** | Public company profiles, org charts from filings, S& capability taxonomy, industry signals, known industry events | Automated ingestion + S& internal data | All users |
| **Personal layer** | Contacts, relationship notes, past proposals, account plans, call notes, custom priorities, uploaded documents | Partner-uploaded | Only that partner |

The recommendation engine always runs against **base + personal combined**. Personal data never leaks across users.

**Design principle:** The base layer makes the tool useful on day one, before a partner uploads anything. The personal layer makes it indispensable over time — the more a partner puts in, the sharper the recommendations get.

### 2.2 Storage

| Store | Technology | Purpose |
|---|---|---|
| **Relational DB** | PostgreSQL | Users, companies, contacts, proposals, relationships, signal metadata, recommendation logs, feedback |
| **Vector DB** | Pinecone or Weaviate | Embeddings of signals, uploaded documents, proposal content — enables semantic matching between signals and company context |
| **Object storage** | Azure Blob (or S3) | Raw uploaded files (proposals, decks, account plans) |

### 2.3 Data isolation

Each partner's personal-layer data is logically siloed at the database level. One partner cannot query, view, or influence another's pipeline, contacts, or proposals. The base layer is shared read-only. Authentication enforces this boundary, not just UI-level hiding.

---

## 3. Core modules

### 3.1 Signal ingestion engine

Aggregates, deduplicates, categorizes, and scores external events relevant to automotive and A&D.

**Sources:**

| Source type | Examples | Ingestion method |
|---|---|---|
| News and press releases | Reuters, WSJ, industry trades (Automotive News, Defense News), OEM newsrooms | News aggregation API (Event Registry, GDELT, or NewsAPI) |
| Government and regulatory | Federal Register, NHTSA, FAA, DOD acquisition portals, executive orders, ITAR/EAR updates | Structured API pulls + scheduled scraping |
| Earnings and filings | SEC EDGAR, investor relations pages | EDGAR API + HTML parsing |
| Leadership changes | Board appointments, C-suite moves | News APIs + LinkedIn monitoring |
| M&A and investment | Deal announcements, JV formations, plant investments | News APIs + PitchBook/Capital IQ (if licensed) |
| Industry events | Conference agendas, trade show announcements | Periodic scraping |
| Government contracts | SAM.gov, GovWin, USASpending | API pulls |

**Processing pipeline:**

1. **Ingest** — Pull from sources on schedule (hourly for news, daily for regulatory, real-time for breaking).
2. **Deduplicate** — Entity resolution across sources. The same GM announcement from 15 outlets becomes one signal.
3. **Classify** — Tag by industry (auto vs. A&D), sub-sector, signal type (regulatory, earnings, leadership, M&A, government action), and affected companies.
4. **Score** — Rate signal importance based on source credibility, affected company size, regulatory impact scope, and recency.
5. **Embed** — Generate vector embeddings for semantic matching against company profiles and uploaded documents.
6. **Store** — Write structured metadata to PostgreSQL, embeddings to vector DB.

### 3.2 Client and relationship graph

A structured intake layer (not a full CRM rebuild) where each partner manages their portfolio.

**Data objects:**

- **Companies** — Name, industry, sub-sector, size, geography, current client status (active / past / target), S& engagement history.
- **Contacts** — Name, title, company, relationship owner (which partner), relationship strength (1–5), last interaction date, notes.
- **Proposals** — Company, date submitted, S& capabilities pitched, outcome (won / lost / pending / no decision), team involved, proposal document (uploaded).
- **Relationships** — Edges connecting partners to contacts and companies. Captures who knows whom and how well.

**Upload flows:**

- Drag-and-drop for proposals, contact lists (CSV/Excel), and account plans.
- Structured forms for adding individual contacts and companies.
- Bulk import from existing CRM export (if partners have Salesforce or Dynamics data).

### 3.3 S& capability taxonomy

A structured, maintained map of what Strategy& sells into auto and A&D. This is required for the recommendation engine to match signals to offerings.

**Example structure:**

```
Strategy & Operations
  ├── Enterprise strategy
  ├── Growth strategy
  ├── Portfolio strategy and M&A
  └── Operating model transformation

Supply Chain & Operations
  ├── Supply chain resilience
  ├── Manufacturing footprint optimization
  ├── EV transition / powertrain strategy
  └── Procurement transformation

Technology & Digital
  ├── Digital transformation strategy
  ├── Data & analytics strategy
  ├── IT operating model
  └── Cybersecurity strategy

Regulatory & Risk
  ├── Regulatory compliance strategy
  ├── Government affairs strategy
  ├── ITAR/EAR compliance
  └── ESG and sustainability strategy

Organization & People
  ├── Organization design
  ├── Workforce transformation
  ├── Change management
  └── Cost transformation / restructuring
```

This taxonomy is a configuration input, not hardcoded. S& leadership can update it as offerings evolve.

### 3.4 Recommendation engine

The intelligence layer. LLM-powered (Claude API) matching that connects signals, companies, relationships, and S& capabilities.

**Recommendation types:**

| Type | Example output |
|---|---|
| **Signal-to-company match** | "Lockheed Martin announced a $2B supply chain overhaul. You have an active relationship with their VP of Strategy. S& has relevant credentials in supply chain resilience." |
| **Outreach recommendation** | "Reach out to [Contact] at [Company] this week. Signal urgency: high. Suggested framing: [talking points]." |
| **Follow-up prompt** | "You submitted a proposal to Stellantis 6 weeks ago with no response. Recent signal: Stellantis just announced a strategic review of NA operations. This is a natural re-engagement opportunity." |
| **Net-new target** | "BAE Systems is expanding its US operations (signal). No existing S& relationship identified. Closest connection: [Partner X] worked with BAE's former CFO at a previous firm." |
| **Capability match** | "Three signals this week point to EV transition pressure at legacy OEMs. Your portfolio includes two OEMs with no active EV-related engagement. Consider pitching powertrain strategy." |

**How matching works:**

1. New signal arrives and is embedded.
2. System computes semantic similarity between the signal embedding and: (a) company profiles in the partner's portfolio, (b) uploaded proposal content, (c) S& capability descriptions.
3. High-similarity matches are passed to the LLM with the partner's relationship context.
4. LLM generates a ranked recommendation with talking points, urgency score, and suggested timing.
5. Recommendation is delivered to the partner's dashboard and/or daily digest.

### 3.5 Feedback loop

Partners mark each recommendation as:
- **Acted on** — contacted the client/target based on this recommendation.
- **Saved for later** — useful but not right now.
- **Not relevant** — bad match, wrong signal, wrong company, wrong timing.

This data feeds back into the recommendation engine to tune relevance scoring per partner over time. Without this, recommendation quality plateaus after launch.

### 3.6 User interface

**Views:**

| View | Purpose |
|---|---|
| **Dashboard** | Today's top signals matched to the partner's portfolio. Filterable by industry, signal type, urgency. |
| **Company detail** | Everything known about a company: recent signals, contacts, proposal history, recommended actions, uploaded context. |
| **Outreach queue** | Prioritized list of who to contact, with draft talking points and suggested timing. Partners can approve, edit, snooze, or dismiss. |
| **Upload center** | Drag-and-drop for proposals, contact lists, account plans, and other supporting documents. |
| **Settings** | Industry focus, notification preferences, sub-sector filters, deal size thresholds. |

**Delivery channels:**
- Web application (primary).
- Daily digest email with top 5 recommendations.
- Mobile-responsive design for partners in transit.

---

## 4. Technical architecture

```
┌──────────────────────────────────────────────────────┐
│                  Frontend (React)                     │
│   Dashboard · Company View · Outreach Queue · Upload  │
└─────────────────────────┬────────────────────────────┘
                          │ REST / GraphQL API
┌─────────────────────────▼────────────────────────────┐
│                Backend (Python / FastAPI)              │
│   Auth · User Mgmt · API Layer · Job Scheduler        │
│   Document Processing · Embedding Pipeline            │
└──┬──────────┬────────────────┬──────────┬────────────┘
   │          │                │          │
   ▼          ▼                ▼          ▼
┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│Ingestion│ │ Vector DB│ │Relational│ │ Object Store │
│Pipeline │ │(Pinecone/│ │   DB     │ │ (Azure Blob) │
│         │ │ Weaviate)│ │(Postgres)│ │              │
│News APIs│ │          │ │          │ │ Raw uploads  │
│Scrapers │ │Embeddings│ │Structured│ │ Proposals    │
│Gov feeds│ │of signals│ │ data     │ │ Decks        │
└────────┘ │& docs    │ └──────────┘ └──────────────┘
           └──────────┘
                │
                ▼
      ┌─────────────────┐
      │   LLM Layer     │
      │  (Claude API)   │
      │                 │
      │ Signal matching │
      │ Recommendations │
      │ Talking points  │
      │ Follow-up logic │
      └─────────────────┘
```

**Key technology choices:**

| Component | Recommended | Rationale |
|---|---|---|
| Frontend | React + TypeScript | Standard, large ecosystem, easy to find developers |
| Backend | Python / FastAPI | Best ecosystem for ML/NLP, fast API framework |
| Relational DB | PostgreSQL | Robust, free, handles complex queries well |
| Vector DB | Pinecone or Weaviate | Purpose-built for embedding search at scale |
| LLM | Claude API | Strong reasoning for nuanced business context |
| Object storage | Azure Blob Storage | Likely required if hosted on PwC Azure infrastructure |
| Job scheduler | Celery + Redis | Handles async ingestion jobs and scheduled scraping |
| Auth | Azure AD / Okta | Integrates with PwC SSO |

---

## 5. Security and compliance considerations

| Concern | Mitigation |
|---|---|
| **Client data isolation** | Row-level security in PostgreSQL. Each partner's personal data is tenant-scoped. API layer enforces access boundaries. |
| **Proposal sensitivity** | Uploaded proposals may contain confidential pricing and strategy. Encrypted at rest and in transit. Access limited to the uploading partner. |
| **Information barriers** | If Partner A works with Company X and Partner B works with Company X's competitor, their data and recommendations must not cross. The personal-layer silo enforces this. |
| **PwC IT policy** | Must be hosted on PwC-approved infrastructure (likely Azure). Must pass firm security review before any pilot with real client data. |
| **Data residency** | If used across geographies, data residency requirements may apply. Design for region-scoped storage from the start. |
| **LLM data handling** | Ensure the Claude API contract permits sending client-adjacent data (company names, proposal summaries). Consider a private deployment or data processing agreement. |

---

## 6. What is not in scope (for now)

- Full CRM replacement (Salesforce, Dynamics).
- Automated email sending or calendar scheduling on behalf of partners.
- Real-time collaboration between partners on shared accounts.
- Integration with PwC's internal billing, staffing, or project management systems.
- Industries beyond automotive and A&D.

These are future phases, not v1.

---

## 7. Open design questions

These need decisions before development begins:

1. **Build vs. extend CRM?** — If S& already uses Salesforce, building the relationship layer on top of it avoids double data entry. Building custom is cleaner but creates an adoption barrier. Need to confirm what CRM infrastructure exists.

2. **Hosting environment** — PwC Azure, external cloud, or hybrid? Compliance will likely mandate firm infrastructure. Confirm with IT early.

3. **Pilot scope** — Recommend starting with one industry (A&D or auto, not both) and 3–5 pilot partners. Validate signal quality and recommendation usefulness before scaling.

4. **Data licensing** — Some sources (PitchBook, Capital IQ, GovWin) require commercial licenses. Determine which are already available within PwC and which need procurement.

5. **Warm introduction routing** — Should the system surface cross-partner relationship paths (anonymized)? e.g., "You don't know GM's VP of Strategy, but someone at the firm does." This is high value but raises information-barrier questions.

6. **Competitive intelligence** — Should the tool attempt to infer what competitors (McKinsey, Deloitte, Accenture) are likely pitching based on the same signals? Useful but harder to build and validate.

---

## 8. Build sequence

| Phase | Scope | Estimated timeline | Exit criteria |
|---|---|---|---|
| **0 — Validate** | Figma mockups of dashboard and outreach queue. Show to 3–5 partners. Gather feedback on signal types, recommendation format, and workflow fit. | 2 weeks | Partners confirm the concept solves a real pain point and would use it. |
| **1 — Signal engine MVP** | News and regulatory ingestion for one industry. Deduplication. Daily email digest of top 10 signals. No personalization. | 4–6 weeks | Partners rate >60% of signals as relevant. |
| **2 — Relationship layer** | Upload contacts, companies, and proposals. Manual signal-to-company matching in the UI. Company detail view. | 4 weeks | 3+ partners have uploaded their portfolio data. |
| **3 — Recommendation engine** | LLM-powered matching. Auto-generated outreach suggestions and talking points. Urgency scoring. Outreach queue view. | 6 weeks | Partners act on >30% of recommendations within one week. |
| **4 — Personalization + feedback** | Per-user preference tuning. Feedback loop on recommendations. Improved matching based on feedback data. | 4 weeks | Recommendation relevance improves measurably based on feedback data. |
| **5 — Scale + integrate** | Second industry. Mobile-responsive design. Email digest refinement. PowerPoint export. Outlook integration (stretch). | Ongoing | — |

**Total to functional MVP (Phases 0–3): ~16–18 weeks.**

---

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Partners don't upload data | High | Tool stays generic, low value | Pre-load base layer so tool is useful on day one. Make uploads frictionless. Show value before asking for input. |
| Signal noise overwhelms usefulness | Medium | Partners ignore the tool | Invest in deduplication and quality scoring in Phase 1. Start with fewer, higher-quality sources. |
| PwC compliance blocks deployment | Medium | Project stalls | Engage IT and Risk & Quality in Phase 0, not Phase 3. |
| LLM recommendations are too generic | Medium | Partners lose trust | Use the feedback loop aggressively. Fine-tune prompts with real partner feedback. Include relationship and proposal context in every recommendation call. |
| Scope creep | High | Timelines slip, MVP never ships | Hold the phase gates. Phase 0 validates before building. No new features until current phase exits. |
