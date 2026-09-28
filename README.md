# Sales Intelligence Platform

A signal intelligence and relationship matching tool that helps Strategy& partners/directors in automotive, energy, and A&D identify, prioritize, and act on sales opportunities.

Built by the IMA AI Pod.

## What it does

Partners already track market signals, client relationships, and S& capabilities — but across email, memory, and scattered files. This platform connects those three streams into a single workflow.

It answers five questions daily:

1. **What just happened?** — Market signals relevant to their portfolio (news, regulation, executive moves, earnings, government action).
2. **Who does it affect?** — Which companies and contacts in their network are impacted.
3. **What should I pitch?** — Which S& capabilities align to the signal and the company's context.
4. **When should I reach out?** — Urgency scoring based on signal recency, relationship warmth, and sales cycle timing.
5. **What do I say?** — Draft talking points connecting the signal, the relationship, and the S& value proposition.

## How it works

The platform ingests public market signals (SEC filings, Federal Register, news APIs, government contracts), deduplicates and classifies them, then matches them against each partner's portfolio of companies, contacts, and past proposals using semantic search and LLM-powered reasoning (Claude API). High-confidence matches surface as prioritized outreach recommendations with draft talking points.

Each partner's data is siloed — one partner's contacts, proposals, and recommendations are never visible to another.

## Project structure

backend/       Python / FastAPI REST API — data models, business logic, auth
frontend/      TypeScript / React UI — dashboard, company views, outreach queue, uploads
ingestion/     Python / Celery pipeline — SEC, Federal Register, GDELT, news ingestion
infra/         Docker, Terraform, CI/CD configuration

## Tech stack

- **Backend:** Python 3.12+ / FastAPI / SQLAlchemy / Alembic
- **Frontend:** TypeScript / React / Vite / Tailwind CSS
- **Database:** PostgreSQL (relational) + Pinecone or Weaviate (vector)
- **LLM:** Claude API (Anthropic)
- **Task queue:** Celery + Redis
- **Object storage:** Azure Blob Storage
- **Infrastructure:** Docker / Terraform (Azure)

## Getting started

> Setup instructions will be added as the local dev environment is finalized.

## Reference docs

- [`Sales_Intelligence_Platform_Project_Plan.md`](Sales_Intelligence_Platform_Project_Plan.md) — Full product spec, architecture, and phased build sequence
- [`Technical_Reference_File_Structure.md`](Technical_Reference_File_Structure.md) — Detailed file tree by build phase# FFG-AI-Pods-IMA-Pod-1
