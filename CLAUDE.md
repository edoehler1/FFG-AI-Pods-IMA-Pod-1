# Sales Intelligence Platform

## Project Context

A signal intelligence and relationship matching tool for Strategy& partners in automotive and A&D. Built by Gabriel Solis and Ethan Doehler as part of the IMA AI Pod.

Two contributors use Claude Code on this repo. Start every session by asking who is working and what changed since the last session.

## Tech Stack

- **Backend:** Python 3.12+ / FastAPI
- **Frontend:** TypeScript / React / Vite / Tailwind CSS
- **Database:** PostgreSQL (relational), Pinecone or Weaviate (vector)
- **LLM:** Claude API (Anthropic)
- **Task queue:** Celery + Redis
- **Object storage:** Azure Blob Storage
- **Infrastructure:** Docker, Terraform (Azure)

## Coding Conventions

### Python (backend + ingestion)
- Use type hints on all function signatures
- Pydantic for request/response schemas
- SQLAlchemy ORM for database models
- Alembic for migrations
- `ruff` for linting and formatting
- Tests with `pytest`

### TypeScript (frontend)
- Functional components only (no class components)
- React hooks for state management
- Axios for API calls
- Component files: PascalCase (e.g., `SignalCard.tsx`)
- Utility files: camelCase (e.g., `formatters.ts`)

### General
- No secrets in code — use environment variables via `.env` (never committed)
- Keep files focused — one module/component per file
- Write tests for API endpoints and core business logic

## Git Workflow

- **main** is the stable branch — never commit directly to main
- Create feature branches: `feature/<short-description>` (e.g., `feature/signal-ingestion`)
- Create fix branches: `fix/<short-description>`
- Open pull requests to merge into main
- Both contributors should review PRs before merging when possible
- Write descriptive commit messages (what changed and why)

## Project Structure

```
backend/         Python / FastAPI backend API
frontend/        TypeScript / React frontend
ingestion/       Python / Celery signal ingestion pipeline
infra/           Docker, Terraform, CI/CD configs
```

## Key Reference Files

- `Sales_Intelligence_Platform_Project_Plan.md` — Full product spec and architecture
- `Technical_Reference_File_Structure.md` — Detailed file tree by phase
- `BUILDERS_GUIDE.md` — Living feasibility assessment, task division, and build roadmap
