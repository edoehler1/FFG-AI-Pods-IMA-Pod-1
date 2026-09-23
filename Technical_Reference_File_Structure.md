# Sales Intelligence Platform — Technical Reference: File Structure

**Companion to:** Sales_Intelligence_Platform_Project_Plan.md
**Purpose:** Complete file tree, languages, and database schema by phase. Use this as the build checklist.

---

## Project root structure

```
sales-intelligence-platform/
├── backend/          (Python / FastAPI)
├── frontend/         (TypeScript / React)
├── ingestion/        (Python / Celery)
├── infra/            (Docker, YAML, Shell, Terraform)
└── shared/           (JSON schemas)
```

---

## Infrastructure (spans all phases)

Built first, extended as needed.

| File | Language | Purpose |
|---|---|---|
| `docker-compose.yml` | YAML | Local dev: Postgres, Redis, vector DB, backend, frontend |
| `infra/Dockerfile.backend` | Dockerfile | Backend container |
| `infra/Dockerfile.frontend` | Dockerfile | Frontend container |
| `infra/Dockerfile.ingestion` | Dockerfile | Ingestion worker container |
| `infra/terraform/main.tf` | Terraform (HCL) | Azure resource provisioning |
| `infra/terraform/variables.tf` | Terraform | Environment-specific config |
| `infra/terraform/outputs.tf` | Terraform | Resource endpoints |
| `.github/workflows/ci.yml` | YAML | CI pipeline — lint, test, build |
| `.github/workflows/deploy.yml` | YAML | CD pipeline — deploy to Azure |
| `.env.example` | Shell | Environment variable template |
| `Makefile` | Make | Common commands (run, test, migrate, seed) |

---

## Phase 1 — Signal Engine MVP

### Backend (Python / FastAPI)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app entry, middleware, CORS
│   ├── config.py                   # Settings from env vars (Pydantic BaseSettings)
│   ├── database.py                 # SQLAlchemy engine, session factory
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── signal.py               # Signal ORM model
│   │   ├── source.py               # Source metadata model
│   │   └── user.py                 # User model (placeholder for Phase 2)
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── signal.py               # Pydantic request/response schemas
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py               # Top-level API router
│   │   └── signals.py              # GET /signals, GET /signals/{id}, filters
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── embedding.py            # Generate embeddings via Claude/OpenAI
│   │   └── email_digest.py         # Compile and send daily top-10 email
│   │
│   └── utils/
│       ├── __init__.py
│       └── logging.py              # Structured logging config
│
├── migrations/
│   ├── env.py                      # Alembic environment
│   ├── alembic.ini                 # Alembic config
│   └── versions/
│       └── 001_initial_schema.py   # Signals, sources tables
│
├── tests/
│   ├── conftest.py                 # Fixtures, test DB
│   ├── test_signals_api.py
│   └── test_email_digest.py
│
├── requirements.txt
└── pyproject.toml
```

### Ingestion Pipeline (Python / Celery)

```
ingestion/
├── __init__.py
├── main.py                         # Celery app entry
├── config.py                       # API keys, source configs, schedules
│
├── sources/
│   ├── __init__.py
│   ├── base.py                     # Abstract source class
│   ├── news_api.py                 # Event Registry / NewsAPI client
│   ├── federal_register.py         # Federal Register API client
│   ├── sec_edgar.py                # SEC EDGAR filings client
│   ├── sam_gov.py                  # Government contracts (SAM.gov)
│   └── rss.py                      # Generic RSS feed parser
│
├── processing/
│   ├── __init__.py
│   ├── deduplication.py            # Entity resolution, fuzzy matching
│   ├── classifier.py               # Industry/type tagging (LLM-assisted)
│   ├── scorer.py                   # Source credibility and importance scoring
│   └── embedder.py                 # Vector embedding generation
│
├── tasks/
│   ├── __init__.py
│   ├── ingest_news.py              # Celery task: hourly news pull
│   ├── ingest_regulatory.py        # Celery task: daily gov/reg pull
│   ├── ingest_filings.py           # Celery task: daily SEC pull
│   └── send_digest.py              # Celery task: daily email digest
│
├── tests/
│   ├── test_deduplication.py
│   ├── test_classifier.py
│   └── test_sources.py
│
└── requirements.txt
```

### Authentication (Python — built in Phase 1, extended later)

```
backend/app/
├── auth/
│   ├── __init__.py
│   ├── azure_ad.py                  # Azure AD / Okta OIDC integration
│   ├── middleware.py                # Auth middleware, token validation
│   ├── dependencies.py             # FastAPI dependency: get_current_user
│   └── row_level_security.py       # Enforce user-scoped DB queries
```

### Database — Phase 1 tables (SQL)

```
signals
├── id                  UUID PRIMARY KEY
├── title               TEXT NOT NULL
├── body                TEXT
├── url                 TEXT
├── source_id           UUID FK → sources
├── published_at        TIMESTAMP
├── industry            VARCHAR (automotive | aerospace_defense)
├── signal_type         VARCHAR (news | regulatory | earnings | leadership | ma | gov_contract)
├── importance_score    FLOAT
├── embedding_id        VARCHAR
├── dedupe_hash         VARCHAR UNIQUE
├── created_at          TIMESTAMP DEFAULT NOW()

sources
├── id                  UUID PRIMARY KEY
├── name                VARCHAR NOT NULL
├── type                VARCHAR (news_api | rss | gov_api | sec | scraper)
├── base_url            TEXT
├── credibility_score   FLOAT
├── last_fetched_at     TIMESTAMP

signal_entities
├── id                  UUID PRIMARY KEY
├── signal_id           UUID FK → signals
├── entity_name         VARCHAR
├── entity_type         VARCHAR (company | person | organization | agency)
├── resolved_entity_id  UUID NULLABLE
```

**Languages in Phase 1:** Python, SQL, YAML, Shell

---

## Phase 2 — Relationship Layer

### Backend additions (Python)

```
backend/app/
├── models/
│   ├── company.py                  # Company ORM model
│   ├── contact.py                  # Contact ORM model
│   ├── proposal.py                 # Proposal ORM model
│   └── relationship.py            # Relationship edges model
│
├── schemas/
│   ├── company.py
│   ├── contact.py
│   ├── proposal.py
│   └── upload.py                   # File upload schemas
│
├── api/
│   ├── companies.py                # CRUD: /companies
│   ├── contacts.py                 # CRUD: /contacts
│   ├── proposals.py                # CRUD: /proposals
│   └── uploads.py                  # POST /uploads (file processing)
│
├── services/
│   ├── upload_parser.py            # Parse CSV, Excel, PDF uploads
│   ├── document_processor.py       # Extract text, embed uploaded docs
│   └── company_enrichment.py       # Enrich company profiles from public data

backend/migrations/versions/
│   └── 002_relationship_tables.py

backend/tests/
├── test_companies_api.py
├── test_contacts_api.py
├── test_uploads.py
└── test_upload_parser.py
```

### Frontend (TypeScript / React)

```
frontend/
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── vite.config.ts
│
├── public/
│   └── index.html
│
├── src/
│   ├── main.tsx                    # App entry
│   ├── App.tsx                     # Root component, routing
│   │
│   ├── api/
│   │   ├── client.ts               # Axios/fetch wrapper, auth headers
│   │   ├── signals.ts              # Signal API calls
│   │   ├── companies.ts            # Company API calls
│   │   ├── contacts.ts             # Contact API calls
│   │   ├── proposals.ts            # Proposal API calls
│   │   └── uploads.ts              # Upload API calls
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx         # Navigation sidebar
│   │   │   ├── Header.tsx          # Top bar, user menu
│   │   │   └── PageLayout.tsx      # Common page wrapper
│   │   │
│   │   ├── common/
│   │   │   ├── DataTable.tsx        # Reusable sortable/filterable table
│   │   │   ├── FileUploader.tsx     # Drag-and-drop upload component
│   │   │   ├── SearchBar.tsx        # Global search
│   │   │   ├── FilterPanel.tsx      # Industry/type/date filters
│   │   │   ├── Badge.tsx            # Status/tag badges
│   │   │   └── Modal.tsx            # Reusable modal
│   │   │
│   │   ├── signals/
│   │   │   ├── SignalCard.tsx        # Individual signal display
│   │   │   └── SignalList.tsx        # Signal feed
│   │   │
│   │   ├── companies/
│   │   │   ├── CompanyCard.tsx       # Company summary card
│   │   │   ├── CompanyDetail.tsx     # Full company view
│   │   │   └── CompanyList.tsx       # Company table
│   │   │
│   │   ├── contacts/
│   │   │   ├── ContactCard.tsx
│   │   │   ├── ContactForm.tsx       # Add/edit contact
│   │   │   └── ContactList.tsx
│   │   │
│   │   └── proposals/
│   │       ├── ProposalCard.tsx
│   │       ├── ProposalForm.tsx
│   │       └── ProposalList.tsx
│   │
│   ├── pages/
│   │   ├── SignalsPage.tsx          # Signal feed view
│   │   ├── CompaniesPage.tsx        # Company list
│   │   ├── CompanyDetailPage.tsx    # Single company view
│   │   ├── ContactsPage.tsx         # Contact list
│   │   ├── ProposalsPage.tsx        # Proposal list
│   │   └── UploadPage.tsx           # Upload center
│   │
│   ├── hooks/
│   │   ├── useSignals.ts
│   │   ├── useCompanies.ts
│   │   ├── useContacts.ts
│   │   └── useAuth.ts               # Auth state hook
│   │
│   ├── types/
│   │   ├── signal.ts
│   │   ├── company.ts
│   │   ├── contact.ts
│   │   └── proposal.ts
│   │
│   └── utils/
│       ├── formatters.ts            # Date, currency, text formatting
│       └── constants.ts             # Industry lists, signal types
│
└── tests/
    ├── components/
    │   └── SignalCard.test.tsx
    └── pages/
        └── CompaniesPage.test.tsx
```

### Database — Phase 2 tables (SQL)

```
companies
├── id                  UUID PRIMARY KEY
├── name                VARCHAR NOT NULL
├── industry            VARCHAR
├── sub_sector          VARCHAR
├── size                VARCHAR (small | mid | large | enterprise)
├── geography           VARCHAR
├── client_status       VARCHAR (active | past | target)
├── user_id             UUID FK → users (owner / data silo)
├── created_at          TIMESTAMP DEFAULT NOW()
├── updated_at          TIMESTAMP

contacts
├── id                  UUID PRIMARY KEY
├── company_id          UUID FK → companies
├── name                VARCHAR NOT NULL
├── title               VARCHAR
├── relationship_strength INTEGER (1-5)
├── last_interaction_date DATE
├── notes               TEXT
├── user_id             UUID FK → users
├── created_at          TIMESTAMP DEFAULT NOW()

proposals
├── id                  UUID PRIMARY KEY
├── company_id          UUID FK → companies
├── date_submitted      DATE
├── capabilities_pitched JSONB
├── outcome             VARCHAR (won | lost | pending | no_decision)
├── team                JSONB
├── document_url        TEXT
├── user_id             UUID FK → users
├── created_at          TIMESTAMP DEFAULT NOW()

relationships
├── id                  UUID PRIMARY KEY
├── user_id             UUID FK → users
├── contact_id          UUID FK → contacts
├── company_id          UUID FK → companies
├── type                VARCHAR (primary | secondary | referral)
├── strength            INTEGER (1-5)

uploaded_documents
├── id                  UUID PRIMARY KEY
├── user_id             UUID FK → users
├── filename            VARCHAR
├── storage_url         TEXT
├── content_hash        VARCHAR
├── embedding_id        VARCHAR
├── processed_at        TIMESTAMP
├── created_at          TIMESTAMP DEFAULT NOW()
```

**Languages in Phase 2:** TypeScript, Python, SQL, CSS (Tailwind), HTML

---

## Phase 3 — Recommendation Engine

### Backend additions (Python)

```
backend/app/
├── models/
│   ├── recommendation.py           # Recommendation ORM model
│   └── outreach.py                 # Outreach queue item model
│
├── schemas/
│   ├── recommendation.py
│   └── outreach.py
│
├── api/
│   ├── recommendations.py          # GET /recommendations, filters, dismiss
│   └── outreach.py                 # GET /outreach-queue, PATCH status
│
├── services/
│   ├── llm_client.py               # Claude API wrapper
│   ├── signal_matcher.py           # Semantic matching: signal to company
│   ├── capability_matcher.py       # Match signals to S& offerings
│   ├── recommendation_engine.py    # Orchestrator: score, rank, generate
│   ├── talking_points.py           # Generate outreach talking points
│   └── urgency_scorer.py           # Score outreach urgency
│
├── data/
│   └── capability_taxonomy.json    # S& capability tree (configurable)

backend/tests/
├── test_signal_matcher.py
├── test_recommendation_engine.py
└── test_talking_points.py
```

### Frontend additions (TypeScript / React)

```
frontend/src/
├── components/
│   ├── dashboard/
│   │   ├── DashboardSummary.tsx     # KPI cards (signals today, pending outreach)
│   │   ├── TopSignals.tsx           # Today's matched signals
│   │   └── RecommendationFeed.tsx   # Scrollable recommendation stream
│   │
│   ├── recommendations/
│   │   ├── RecommendationCard.tsx   # Signal + company + action in one card
│   │   ├── TalkingPoints.tsx        # Expandable talking points section
│   │   └── UrgencyBadge.tsx         # Visual urgency indicator
│   │
│   └── outreach/
│       ├── OutreachQueue.tsx        # Prioritized outreach list
│       ├── OutreachItem.tsx         # Single outreach action
│       └── OutreachActions.tsx      # Approve / edit / snooze / dismiss
│
├── pages/
│   ├── DashboardPage.tsx            # Main dashboard
│   └── OutreachPage.tsx             # Outreach queue view
│
├── api/
│   ├── recommendations.ts
│   └── outreach.ts
│
├── hooks/
│   ├── useRecommendations.ts
│   └── useOutreach.ts
│
└── types/
    ├── recommendation.ts
    └── outreach.ts
```

### Database — Phase 3 tables (SQL)

```
recommendations
├── id                  UUID PRIMARY KEY
├── user_id             UUID FK → users
├── signal_id           UUID FK → signals
├── company_id          UUID FK → companies
├── contact_id          UUID FK → contacts NULLABLE
├── capability_match    JSONB
├── urgency_score       FLOAT
├── talking_points      TEXT
├── status              VARCHAR (new | acted | dismissed | snoozed)
├── snoozed_until       TIMESTAMP NULLABLE
├── created_at          TIMESTAMP DEFAULT NOW()

outreach_items
├── id                  UUID PRIMARY KEY
├── recommendation_id   UUID FK → recommendations
├── user_id             UUID FK → users
├── scheduled_date      DATE
├── follow_up_date      DATE NULLABLE
├── status              VARCHAR (pending | completed | skipped)
├── notes               TEXT
├── created_at          TIMESTAMP DEFAULT NOW()
```

**Languages in Phase 3:** Python, TypeScript, SQL, JSON

---

## Phase 4 — Personalization + Feedback

### Backend additions (Python)

```
backend/app/
├── models/
│   ├── feedback.py                  # Feedback on recommendations
│   └── user_preferences.py         # Per-user settings and filters
│
├── schemas/
│   ├── feedback.py
│   └── preferences.py
│
├── api/
│   ├── feedback.py                  # POST /feedback, GET /feedback/stats
│   └── preferences.py              # GET/PUT /preferences
│
├── services/
│   ├── feedback_analyzer.py         # Aggregate feedback into tuning signals
│   └── preference_engine.py         # Apply user prefs to recommendation ranking

backend/tests/
├── test_feedback.py
└── test_preference_engine.py
```

### Frontend additions (TypeScript / React)

```
frontend/src/
├── components/
│   ├── feedback/
│   │   ├── FeedbackButtons.tsx      # Acted on / saved / not relevant
│   │   └── FeedbackSummary.tsx      # Feedback stats over time
│   │
│   └── settings/
│       ├── IndustryFilters.tsx       # Toggle sub-sectors
│       ├── NotificationPrefs.tsx     # Digest frequency, alert thresholds
│       └── DealSizeFilter.tsx        # Min deal size threshold
│
├── pages/
│   └── SettingsPage.tsx
│
└── api/
    ├── feedback.ts
    └── preferences.ts
```

### Database — Phase 4 tables (SQL)

```
feedback
├── id                  UUID PRIMARY KEY
├── recommendation_id   UUID FK → recommendations
├── user_id             UUID FK → users
├── rating              VARCHAR (acted | saved | irrelevant)
├── notes               TEXT
├── created_at          TIMESTAMP DEFAULT NOW()

user_preferences
├── id                  UUID PRIMARY KEY
├── user_id             UUID FK → users UNIQUE
├── industry_filters    JSONB
├── sub_sector_filters  JSONB
├── notification_frequency VARCHAR (realtime | daily | weekly)
├── deal_size_min       INTEGER NULLABLE
├── signal_type_weights JSONB
├── updated_at          TIMESTAMP
```

**Languages in Phase 4:** Python, TypeScript, SQL

---

## Language summary

| Language | Where used | Approximate file count |
|---|---|---|
| **Python** | Backend API, ingestion pipeline, LLM integration, auth | 60-70 files |
| **TypeScript** | Frontend components, pages, hooks, API clients, types | 50-60 files |
| **SQL** | Database schema, migrations | 8-10 migration files |
| **HTML / CSS** | Frontend templates, Tailwind styling | ~5 files |
| **YAML** | Docker, CI/CD, config | 5-8 files |
| **HCL (Terraform)** | Azure infrastructure provisioning | 3-5 files |
| **JSON** | Schemas, capability taxonomy, package config | 5-8 files |
| **Shell / Make** | Scripts, Makefile | 2-3 files |

**Total: approximately 140-170 files across the full build.**
**Two primary languages: Python (backend) and TypeScript (frontend).**
