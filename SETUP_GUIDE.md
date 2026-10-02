# Sales Intelligence Platform — Setup Guide

Everything a new contributor needs to clone, configure, and run the platform locally.

---

## Prerequisites

Install these before starting:

| Tool | Version | Install |
|---|---|---|
| **Git** | Any recent | [git-scm.com](https://git-scm.com/) |
| **Python** | 3.12+ | [python.org](https://www.python.org/downloads/) — check "Add to PATH" during install |
| **Node.js** | 20+ (LTS) | Install via **fnm** (recommended) or [nodejs.org](https://nodejs.org/) |
| **fnm** (optional) | Latest | `winget install Schniz.fnm` — the launch script expects fnm by default |

If you use fnm, run this once after install:
```powershell
fnm install --lts
fnm use lts-latest
```

If you install Node directly (not via fnm), you will need to modify `start.ps1` or launch the frontend manually (covered in Step 6).

---

## Step 1: Clone the Repository

```powershell
cd C:\Users\YourName\Projects     # or wherever you keep code
git clone https://github.com/edoehler1/FFG-AI-Pods-IMA-Pod-1.git
cd FFG-AI-Pods-IMA-Pod-1
```

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

The database starts with companies and contacts but no news signals. Run ingestion to populate them:

```powershell
cd backend

# Run one source at a time:
..\.venv\Scripts\python -m ingestion.run --source news
..\.venv\Scripts\python -m ingestion.run --source sec_edgar
..\.venv\Scripts\python -m ingestion.run --source federal_register
..\.venv\Scripts\python -m ingestion.run --source gdelt
..\.venv\Scripts\python -m ingestion.run --source event_registry
..\.venv\Scripts\python -m ingestion.run --source sam_gov
..\.venv\Scripts\python -m ingestion.run --source usaspending

cd ..
```

Each source fetches data from public APIs and stores signals in your database. The seed step (Step 5) also runs signal-company matching, but you can trigger it again after ingesting new signals by re-running `seed.py`.

---

## Step 8: MCP Enrichment (Optional — Claude Code Users)

The platform has 14 MCP enrichers that pull data from PwC-internal and licensed sources (CapIQ, BoardEx, Factiva, Salesforce, People Connector, etc.). These run through Claude Code's MCP tool connections, not through API keys.

### To use MCP enrichment:

1. You must have Claude Code installed with the relevant MCP servers configured in your session. The MCP server config files (`.claude/` directory contents) are included in the repo but the **server connections themselves** must be set up at the user/session level — they are not portable across machines.

2. If your Claude Code session has access to the MCP tools (company-and-market-research, news, people-connector, salesforce, sec, thought-leadership), you can run enrichment:

```powershell
cd backend
..\.venv\Scripts\python -m ingestion.enrich --mcp all
cd ..
```

Or target a specific source:
```powershell
..\.venv\Scripts\python -m ingestion.enrich --mcp capiq
..\.venv\Scripts\python -m ingestion.enrich --mcp people_connector
..\.venv\Scripts\python -m ingestion.enrich --mcp salesforce
```

3. If you do not have the MCP servers, the platform still works — you just will not have PwC-specific relationship data, financial intelligence, or Salesforce pipeline data in the weekly briefings and profiles.

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

Copy the block below into Claude Code (or paste it as a prompt) to have it walk through every setup step automatically. Replace the placeholder values before running.

````
I need you to set up the Sales Intelligence Platform project. Here is the context and the steps. Execute each step, verify it worked, and move to the next.

## Project location
The repo has already been cloned to: [PASTE YOUR PROJECT PATH HERE, e.g. C:\Users\YourName\Projects\FFG-AI-Pods-IMA-Pod-1]

## What this project is
A FastAPI + React signal intelligence platform. Backend is Python 3.12+ with FastAPI, frontend is TypeScript/React/Vite/Tailwind. Database is SQLite by default (auto-created at data/signals.db). The app proxies frontend /api calls to the backend on port 8000.

## Setup steps — execute in order

### 1. Python virtual environment
- Create a venv at `backend\.venv` using Python 3.12+: `python -m venv backend\.venv`
- Install backend deps: `backend\.venv\Scripts\pip install -r backend\requirements.txt`
- Install ingestion deps: `backend\.venv\Scripts\pip install -r ingestion\requirements.txt`
- Verify: `backend\.venv\Scripts\python -c "import fastapi; print(fastapi.__version__)"`

### 2. Node dependencies
- Ensure Node 20+ is available: `node --version`
- Install frontend deps: run `npm install` from inside the `frontend\` directory
- Verify: confirm `frontend\node_modules` exists

### 3. Environment file
- If `.env` does not exist in the project root, copy `.env.example` to `.env`
- The user needs to fill in their own API key. Prompt them:
  - ANTHROPIC_API_KEY is required (get one at console.anthropic.com)
  - DATABASE_URL can be left unset for local SQLite
  - NEWS_API_KEY, SAM_GOV_API_KEY, EVENT_REGISTRY_API_KEY are optional
- Do NOT overwrite an existing `.env` — it may already have keys configured

### 4. Seed the database
- Run from the project root: `backend\.venv\Scripts\python -c "import os; os.chdir('backend'); exec(open('seed.py').read())"`
  OR: `cd backend` then `..\.venv\Scripts\python seed.py` then `cd ..`
- Verify: confirm `data\signals.db` exists (or that the PostgreSQL tables were created if DATABASE_URL is set)

### 5. Launch
- Start the backend: `backend\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000` (working directory must be `backend\`)
- Start the frontend: `npx vite` from `frontend\` directory (or `npm run dev`)
- Verify: hit http://localhost:8000/docs (should return the FastAPI Swagger UI) and http://localhost:5173 (should load the React app)

### 6. Optional — Signal ingestion
After the app is running, the user can populate signals:
```
cd backend
..\.venv\Scripts\python -m ingestion.run --source news
..\.venv\Scripts\python -m ingestion.run --source sec_edgar
..\.venv\Scripts\python -m ingestion.run --source gdelt
..\.venv\Scripts\python -m ingestion.run --source federal_register
```
Each source is independent. All use public APIs except `news` (needs NEWS_API_KEY) and `event_registry` (needs EVENT_REGISTRY_API_KEY).

### 7. Optional — MCP enrichment
If the Claude Code session has MCP server access (company-and-market-research, news, people-connector, salesforce, sec, thought-leadership), run:
```
cd backend
..\.venv\Scripts\python -m ingestion.enrich --mcp all
```
These MCP servers are configured at the user/session level. They are NOT portable — each user needs their own MCP server connections configured in their Claude Code environment. If the MCP tools are not available, skip this step and notify the user that MCPs are not setup, telling them how and where to add them to the system. The app works without enrichment data.

## Key files for reference
- `BUILDERS_GUIDE.md` — most comprehensive architecture doc
- `DEMO_WALKTHROUGH.md` — step-by-step demo using Boeing as an example
- `backend\app\config.py` — all environment variable defaults
- `backend\app\main.py` — FastAPI entry point, auto-creates tables on startup
- `frontend\vite.config.ts` — dev server proxy config (/api -> localhost:8000)
- `.env.example` — template for environment variables

## Constraints
- Do not modify any existing files during setup
- Do not commit .env or credentials
- Do not push to the remote repository
- If any step fails, diagnose and report the error before continuing
````

---

File: `SETUP_GUIDE.md`
Location: Project root (`FFG-AI-Pods-IMA-Pod-1/`)
