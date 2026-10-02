# Sales Intelligence Platform — Setup Guide

Everything a new contributor needs to clone, configure, and run the platform locally.

## How This Works

Most of the setup is handled by Claude Code. Your job is three things:

1. **Clone the repo** (Step 1 below) — you must do this yourself before opening Claude Code.
2. **Install prerequisites** (Python, Node) — Claude Code cannot install system-level software for you.
3. **Open Claude Code in the cloned folder** and paste the setup prompt from the bottom of this file. Claude Code handles everything else: creating the virtual environment, installing dependencies, configuring the environment file, seeding the database, and launching the app.

If you prefer to set up manually without Claude Code, every step is also written out in full below.

---

## Prerequisites

Install these before starting. Claude Code cannot do these for you — they require system-level access.

| Tool | Version | Install |
|---|---|---|
| **Git** | Any recent | [git-scm.com](https://git-scm.com/) |
| **Python** | 3.12+ | [python.org](https://www.python.org/downloads/) — check "Add to PATH" during install |
| **Node.js** | 20+ (LTS) | Install via **fnm** (recommended) or [nodejs.org](https://nodejs.org/) |
| **fnm** (optional) | Latest | `winget install Schniz.fnm` — the launch script expects fnm by default |
| **Claude Code** (recommended) | Latest | [claude.ai/code](https://claude.ai/code) — CLI, desktop app, or IDE extension |

If you use fnm, run this once after install:
```powershell
fnm install --lts
fnm use lts-latest
```

If you install Node directly (not via fnm), you will need to modify `start.ps1` or launch the frontend manually (covered in Step 6).

---

## Step 1: Clone the Repository

Do this first, before opening Claude Code. Claude Code needs to open inside the cloned folder.

```powershell
cd C:\Users\YourName\Projects     # or wherever you keep code
git clone https://github.com/edoehler1/FFG-AI-Pods-IMA-Pod-1.git
cd FFG-AI-Pods-IMA-Pod-1
```

**If you are using Claude Code:** After cloning, open Claude Code in the `FFG-AI-Pods-IMA-Pod-1` folder, then skip to the [Claude Code Setup Prompt](#for-claude-code-users-full-setup-prompt) section at the bottom of this file. Copy and paste that prompt and Claude Code will walk you through the rest.

**If you are setting up manually:** Continue with Step 2 below.

---

## Step 2: Create the Python Virtual Environment

```powershell
python -m venv backend\.venv
```

Activate it (you will need to do this any time you open a new terminal for backend work):
```powershell
backend\.venv\Scripts\Activate.ps1
```

Install backend dependencies:
```powershell
pip install -r backend\requirements.txt
```

Install ingestion dependencies (same venv):
```powershell
pip install -r ingestion\requirements.txt
```

---

## Step 3: Install Frontend Dependencies

```powershell
cd frontend
npm install
cd ..
```

---

## Step 4: Configure Environment Variables

Copy the example file:
```powershell
Copy-Item .env.example .env
```

Open `.env` in a text editor and fill in your keys:

```env
# REQUIRED — Claude API key (get one at console.anthropic.com)
ANTHROPIC_API_KEY=sk-ant-XXXXX

# DATABASE — leave blank for local SQLite (auto-creates data/signals.db)
# Set to a PostgreSQL URL if using Supabase or another hosted DB:
# DATABASE_URL=postgresql://user:pass@host:5432/dbname

# OPTIONAL — additional data sources (the app works without these)
NEWS_API_KEY=           # newsapi.org — free tier, 100 requests/day
SAM_GOV_API_KEY=        # sam.gov — free, register at sam.gov/content/entity-information
EVENT_REGISTRY_API_KEY= # eventregistry.org — free tier, 2000 queries/month

# Leave these alone unless you know what they are
APP_ENV=development
```

### What each key does

| Variable | Required? | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | Powers all LLM features: signal classification, company profiles, weekly briefings, curated news |
| `DATABASE_URL` | No | Leave unset for SQLite (simplest). Set to a PostgreSQL connection string for shared/persistent DB |
| `NEWS_API_KEY` | No | Adds NewsAPI as an ingestion source. Free tier at [newsapi.org](https://newsapi.org/) |
| `SAM_GOV_API_KEY` | No | Pulls government contract data. Free at [sam.gov](https://sam.gov/) |
| `EVENT_REGISTRY_API_KEY` | No | Adds Event Registry news aggregation. Free tier at [eventregistry.org](https://eventregistry.org/) |

The following data sources require **no API key** (public APIs): SEC EDGAR, Federal Register, GDELT, USASpending, Google News RSS.

---

## Step 5: Seed the Database

This loads the starting set of companies, contacts, and enrichment data:

```powershell
cd backend
..\.venv\Scripts\python seed.py
cd ..
```

You should see output like:
```
Companies: 21 created, 0 already existed
Contacts: XX created
Signal-company matches: XX new links created
Enrichments: XX created, 0 already existed

Seed complete.
```

---

## Step 6: Launch the Application

### Option A: Use the launch script (requires fnm)

```powershell
.\start.ps1
```

This starts both servers and prints:
```
Frontend:  http://localhost:5173
Backend:   http://localhost:8000
API docs:  http://localhost:8000/docs
```

Press `Ctrl+C` to stop both.

### Option B: Start manually (two terminals)

**Terminal 1 — Backend:**
```powershell
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```powershell
cd frontend
npx vite
```

The frontend dev server proxies `/api` requests to the backend automatically, so open **http://localhost:5173** in your browser.

---

## Step 7: Ingest Signals (Optional)

The database starts with companies and contacts but no news signals. Run ingestion to populate them.

**Important:** Ingestion commands must run from the **project root** (where the `ingestion/` folder lives), not from `backend/`.

```powershell
# From the project root (FFG-AI-Pods-IMA-Pod-1\):
backend\.venv\Scripts\python -m ingestion.run --source news
backend\.venv\Scripts\python -m ingestion.run --source sec_edgar
backend\.venv\Scripts\python -m ingestion.run --source federal_register
backend\.venv\Scripts\python -m ingestion.run --source gdelt
backend\.venv\Scripts\python -m ingestion.run --source event_registry
backend\.venv\Scripts\python -m ingestion.run --source sam_gov
backend\.venv\Scripts\python -m ingestion.run --source usaspending
```

Each source is independent — run whichever ones you want. After ingesting, the script automatically runs signal-company matching on the new signals.

Available sources and their requirements:

| Source | API Key Needed? | Notes |
|---|---|---|
| `news` | `NEWS_API_KEY` | Google News RSS (free, no key) + NewsAPI (optional, needs key) |
| `sec_edgar` | No | SEC EDGAR public API |
| `federal_register` | No | Federal Register public API |
| `gdelt` | No | GDELT global news/events |
| `event_registry` | `EVENT_REGISTRY_API_KEY` | Event Registry news aggregation |
| `sam_gov` | `SAM_GOV_API_KEY` | Government contracts |
| `usaspending` | No | Federal spending data |

---

## Step 8: MCP Enrichment (Optional — Claude Code Users)

The platform has 14 MCP enrichers that pull data from PwC-internal and licensed sources (CapIQ, BoardEx, Factiva, Salesforce, People Connector, etc.). These run through Claude Code's MCP tool connections, not through API keys.

### To use MCP enrichment:

1. You must have Claude Code installed with the relevant MCP servers configured in your environment. The MCP server connections are configured at the **user/session level** — they are not included in the repo and are not portable across machines. Each user needs to add the MCP servers to their own Claude Code settings (in `~/.claude/settings.json` or the project `.claude/settings.json`).

   The six MCP server groups the enrichers call:
   - `company-and-market-research-mcp` — CapIQ, BoardEx, Earnings, EMIS, IBISWorld
   - `news-mcp` — Factiva, web search
   - `people-connector-tools-gateway` — People Connector (engagements, relationships)
   - `salesforce-mcp` — Salesforce CRM pipeline data
   - `sec-mcp` — SEC EDGAR filing analysis (risk factors, MD&A)
   - `thought-leadership-mcp` — Connected Sources, VIM, CEO Survey

2. Enrichment commands run from the **project root** (where the `ingestion/` folder lives):

```powershell
# Run all enrichers (omit --mcp to run everything):
backend\.venv\Scripts\python -m ingestion.enrich

# Or target a specific source:
backend\.venv\Scripts\python -m ingestion.enrich --mcp capiq
backend\.venv\Scripts\python -m ingestion.enrich --mcp people_engagements
backend\.venv\Scripts\python -m ingestion.enrich --mcp salesforce
backend\.venv\Scripts\python -m ingestion.enrich --mcp boardex
backend\.venv\Scripts\python -m ingestion.enrich --mcp earnings
backend\.venv\Scripts\python -m ingestion.enrich --mcp factiva
backend\.venv\Scripts\python -m ingestion.enrich --mcp ibis
backend\.venv\Scripts\python -m ingestion.enrich --mcp sec_mcp_risk
backend\.venv\Scripts\python -m ingestion.enrich --mcp sec_mcp_mda
```

   Available `--mcp` values for company enrichers: `capiq`, `boardex`, `earnings`, `emis`, `factiva`, `web`, `sec_mcp_risk`, `sec_mcp_mda`, `salesforce`, `people_engagements`

   Available `--mcp` values for industry enrichers: `ibis`, `connectedsource`, `vim`, `ceo_survey`

   Other useful flags:
   - `--company "Boeing"` — run enrichment for one company only
   - `--industry automotive` — run industry enrichers for one industry only
   - `--force` — ignore staleness checks and refresh everything

3. If you do not have the MCP servers configured, the platform still works — you just will not have PwC-specific relationship data, financial intelligence, or Salesforce pipeline data in the weekly briefings and profiles. The app degrades gracefully when enrichment data is absent.

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set" or LLM calls fail
- Confirm `.env` exists in the project root (not inside `backend/` or `frontend/`)
- Confirm the key starts with `sk-ant-` (Anthropic direct) or is a valid gateway token
- Restart the backend after editing `.env`

### "Could not find fnm node installation"
- This error comes from `start.ps1`. Either install fnm (`winget install Schniz.fnm`) and run `fnm install --lts`, or launch the frontend manually with `npx vite` in the `frontend/` folder

### Frontend shows blank page or API errors
- Make sure the backend is running on port 8000
- Check the backend terminal for Python errors
- Visit http://localhost:8000/docs to confirm the API is responding

### Database errors
- If using SQLite: delete `data/signals.db` and re-run `seed.py` to start fresh
- If using PostgreSQL: confirm your `DATABASE_URL` is correct and the database is accessible

### Module not found errors (Python)
- Make sure you activated the venv: `backend\.venv\Scripts\Activate.ps1`
- Make sure you installed both `backend\requirements.txt` and `ingestion\requirements.txt`

---

## Project Structure (Quick Reference)

```
FFG-AI-Pods-IMA-Pod-1/
  .env                  # Your API keys (not committed to git)
  start.ps1             # Launch script (both servers)
  backend/
    .venv/              # Python virtual environment (you create this)
    app/                # FastAPI application
      main.py           # Entry point
      api/              # API route handlers
      models/           # Database models
      services/         # Business logic (LLM calls, reports, matching)
    seed.py             # Database seeder
    seed_data/          # Starting companies, contacts, enrichments
    requirements.txt
  frontend/
    src/                # React application
      pages/            # Dashboard, Signals, Companies, Reports, etc.
      components/       # UI components
      api/              # API client modules
    package.json
  ingestion/
    run.py              # CLI for signal ingestion
    enrich.py           # MCP enrichment runner
    sources/            # Data source clients (SEC, GDELT, RSS, etc.)
    enrichment/         # 14 MCP enricher modules
    requirements.txt
  data/                 # SQLite database lives here (auto-created, gitignored)
```

---

## For Claude Code Users: Full Setup Prompt

**Before you paste this:** You must have already cloned the repo (Step 1) and opened Claude Code inside the `FFG-AI-Pods-IMA-Pod-1` folder. You also need Python 3.12+ and Node.js 20+ installed on your machine — Claude Code cannot install those for you.

Once those are done, copy the entire block below and paste it into Claude Code. It will handle everything else. Replace `[PASTE YOUR PROJECT PATH HERE]` with the actual path to your cloned repo.

````
I need you to set up the Sales Intelligence Platform project. Here is the full context and every step. Execute each step in order, verify it worked, and move to the next. If a step fails, diagnose and report the error before continuing.

## Project location
The repo has already been cloned to: [PASTE YOUR PROJECT PATH HERE, e.g. C:\Users\YourName\Projects\FFG-AI-Pods-IMA-Pod-1]

All commands below assume you are in the project root directory. Do not cd out of it unless instructed.

## What this project is
A FastAPI + React signal intelligence platform for Strategy& partners. Backend: Python 3.12+ / FastAPI / SQLAlchemy. Frontend: TypeScript / React 19 / Vite / Tailwind CSS. Database: SQLite by default (auto-created at data/signals.db), optional PostgreSQL via DATABASE_URL. The Vite dev server proxies /api requests to the FastAPI backend on port 8000.

## Architecture notes
- Backend entry point: backend/app/main.py — creates all database tables on startup via Base.metadata.create_all()
- Frontend entry point: frontend/src/App.tsx — React Router with pages for Dashboard, Signals, Companies, Reports
- Ingestion pipeline: ingestion/run.py — CLI that fetches signals from public APIs (SEC, GDELT, RSS, etc.)
- MCP enrichment: ingestion/enrich.py — 14 enrichers that call MCP tools for PwC-internal data sources
- Config: backend/app/config.py reads .env from the project root via pydantic-settings
- Seed data: backend/seed_data/ contains sample companies, contacts, and People Connector enrichments

## Setup steps — execute in order

### 1. Check prerequisites
- Verify Python 3.12+: run `python --version`. If not installed or wrong version, stop and tell the user to install Python 3.12+ from python.org and check "Add to PATH" during install.
- Verify Node.js 20+: run `node --version`. If not installed, tell the user to either:
  (a) Install fnm: `winget install Schniz.fnm`, then `fnm install --lts` and `fnm use lts-latest`
  (b) Install Node directly from nodejs.org (LTS version)
  The launch script start.ps1 expects fnm. If Node is installed directly (not via fnm), the user will need to launch the frontend manually instead of using start.ps1.

### 2. Create the Python virtual environment
- Run from the project root: `python -m venv backend\.venv`
- Install backend dependencies: `backend\.venv\Scripts\pip install -r backend\requirements.txt`
- Install ingestion dependencies (same venv): `backend\.venv\Scripts\pip install -r ingestion\requirements.txt`
- Verify: run `backend\.venv\Scripts\python -c "import fastapi; print(fastapi.__version__)"` — should print a version number

### 3. Install frontend dependencies
- Run from the project root: change to the frontend directory, run `npm install`, then change back to the project root
- Verify: confirm `frontend\node_modules\.package-lock.json` exists

### 4. Configure environment variables
- Check if `.env` exists in the project root. If it does, do NOT overwrite it — it may already have keys.
- If `.env` does not exist, copy `.env.example` to `.env`
- Ask the user to provide their ANTHROPIC_API_KEY. This is REQUIRED — the app's LLM features (classification, profiles, weekly briefings) will not work without it. They can get a key at console.anthropic.com.
- The following are optional and the user can leave them blank:
  - DATABASE_URL — leave unset for local SQLite (simplest option)
  - NEWS_API_KEY — enables NewsAPI ingestion source (free at newsapi.org)
  - SAM_GOV_API_KEY — enables SAM.gov contract data (free at sam.gov)
  - EVENT_REGISTRY_API_KEY — enables Event Registry news aggregation (free at eventregistry.org)
- After the user provides the key, write it into .env on the ANTHROPIC_API_KEY line. Do not touch other lines if values exist.

### 5. Seed the database
- Run from the project root: change to the backend directory, run `..\.venv\Scripts\python seed.py`, then change back to the project root
- Expected output: "Companies: 21 created", "Contacts: XX created", "Signal-company matches: XX new links", "Enrichments: XX created", "Seed complete."
- Verify: if DATABASE_URL is unset, confirm `data\signals.db` exists in the project root

### 6. Launch the application
Start both servers. You need two separate processes:

Backend (must run from the backend/ directory):
- Change to the backend directory, then run: `..\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000`

Frontend (must run from the frontend/ directory):
- In a second process, change to the frontend directory, then run: `npx vite`

Alternatively, if fnm is installed, the user can run `.\start.ps1` from the project root, which launches both.

Verify:
- Backend: open http://localhost:8000/docs — should show the FastAPI Swagger UI
- Frontend: open http://localhost:5173 — should load the React dashboard

### 7. Optional — Signal ingestion
After the app is running, the user can populate news signals. These commands run from the PROJECT ROOT (not backend/):
```
backend\.venv\Scripts\python -m ingestion.run --source news
backend\.venv\Scripts\python -m ingestion.run --source sec_edgar
backend\.venv\Scripts\python -m ingestion.run --source gdelt
backend\.venv\Scripts\python -m ingestion.run --source federal_register
backend\.venv\Scripts\python -m ingestion.run --source event_registry
backend\.venv\Scripts\python -m ingestion.run --source sam_gov
backend\.venv\Scripts\python -m ingestion.run --source usaspending
```
Each source is independent. Most use public APIs (no key). `news` benefits from NEWS_API_KEY, and `event_registry` requires EVENT_REGISTRY_API_KEY. The script automatically runs signal-company matching after ingestion.

IMPORTANT: The `python -m ingestion.run` command must execute from the project root, because `ingestion/` is a Python package at that level. Running it from inside `backend/` will fail with "No module named ingestion."

### 8. Optional — MCP enrichment (PwC-internal data sources)
The platform has 14 MCP enrichers that call PwC-internal MCP tools (CapIQ, BoardEx, Factiva, Salesforce, People Connector, etc.). These require MCP server connections configured in the Claude Code environment.

The six MCP server groups the enrichers call:
- company-and-market-research-mcp (CapIQ, BoardEx, Earnings, EMIS, IBISWorld)
- news-mcp (Factiva, web search)
- people-connector-tools-gateway (People Connector engagement data)
- salesforce-mcp (Salesforce CRM pipeline data)
- sec-mcp (SEC EDGAR filing analysis)
- thought-leadership-mcp (Connected Sources, VIM, CEO Survey)

MCP servers are configured at the user/session level, typically in `~/.claude/settings.json` or in the project's `.claude/settings.json`. They are NOT included in the git repo and are NOT portable across machines. If the MCP tools are not available in this Claude Code session, tell the user that MCP enrichment requires MCP server connections to be configured, list the six server groups above, and explain they need to add them to their Claude Code settings. Then skip this step — the app works without enrichment data.

If MCP tools are available, run from the PROJECT ROOT:
```
backend\.venv\Scripts\python -m ingestion.enrich
```
This lists all needed enrichment tasks. To run a specific enricher:
```
backend\.venv\Scripts\python -m ingestion.enrich --mcp capiq
backend\.venv\Scripts\python -m ingestion.enrich --mcp people_engagements
backend\.venv\Scripts\python -m ingestion.enrich --mcp salesforce
```
Available --mcp values:
- Company: capiq, boardex, earnings, emis, factiva, web, sec_mcp_risk, sec_mcp_mda, salesforce, people_engagements
- Industry: ibis, connectedsource, vim, ceo_survey

Other flags: --company "Boeing" (one company), --industry automotive (one industry), --force (ignore staleness)

## Key files for reference
- `SETUP_GUIDE.md` — this setup guide (the source of these instructions)
- `BUILDERS_GUIDE.md` — most comprehensive architecture doc, known issues, design decisions
- `DEMO_WALKTHROUGH.md` — step-by-step demo using Boeing as an example
- `backend\app\config.py` — all environment variable defaults and their types
- `backend\app\main.py` — FastAPI entry point, auto-creates tables + runs migrations on startup
- `backend\app\database.py` — SQLAlchemy engine config, auto-creates data/ directory for SQLite
- `frontend\vite.config.ts` — Vite dev server proxy config (/api -> localhost:8000)
- `.env.example` — template for environment variables with comments
- `ingestion\run.py` — CLI runner for signal ingestion (lists all available sources)
- `ingestion\enrich.py` — CLI runner for MCP enrichment (lists all available enrichers)

## Constraints
- Do not modify any existing source files during setup
- Do not commit .env or any credentials to git
- Do not push to the remote repository
- If any step fails, diagnose the root cause and report the error before continuing
- Do not fabricate or guess API keys — always ask the user
````
