import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_weekly_report_columns()
    _load_enrichment_seeds()
    _load_client_contacts_seeds()
    _categorize_uncategorized()
    yield


def _ensure_weekly_report_columns():
    from sqlalchemy import text
    db = SessionLocal()
    new_cols = [
        ("urgency", "VARCHAR(10)"),
        ("opportunity_summary", "TEXT"),
        ("suggested_lead", "TEXT"),
        ("financial_cross_ref", "TEXT"),
        ("top_signal_title", "TEXT"),
    ]
    for col_name, col_type in new_cols:
        try:
            db.execute(text(f"ALTER TABLE weekly_reports ADD COLUMN {col_name} {col_type}"))
            db.commit()
        except Exception:
            db.rollback()
    db.close()


def _load_enrichment_seeds():
    import json
    import uuid
    from datetime import datetime, timedelta
    from app.models.mcp_enrichment import MCPEnrichment
    from app.models.company import Company

    seed_file = os.path.join(os.path.dirname(__file__), "..", "seed_data", "people_connector_enrichments.json")
    if not os.path.exists(seed_file):
        return

    db = SessionLocal()
    try:
        existing_count = db.query(MCPEnrichment).filter(MCPEnrichment.mcp_source == "people_engagements").count()
        if existing_count > 0:
            return

        with open(seed_file) as f:
            records = json.load(f)

        now = datetime.utcnow()
        loaded = 0
        for record in records:
            company = db.query(Company).filter(Company.name == record["company_name"]).first()
            if not company:
                continue
            db.add(MCPEnrichment(
                id=str(uuid.uuid4()),
                entity_type="company",
                entity_id=company.id,
                mcp_source="people_engagements",
                query_prompt=record.get("query_prompt", ""),
                response_markdown=record.get("response_markdown", ""),
                response_summary=json.dumps(record["response_summary"]) if record.get("response_summary") else None,
                fetched_at=now,
                stale_after=now + timedelta(days=30),
            ))
            loaded += 1
        db.commit()
        if loaded:
            print(f"Loaded {loaded} People Connector enrichments from seed data.")
    except Exception as e:
        print(f"Enrichment seed loading skipped: {e}")
        db.rollback()
    finally:
        db.close()


def _load_client_contacts_seeds():
    import json
    import uuid as _uuid
    from app.models.contact import Contact
    from app.models.company import Company

    seed_file = os.path.join(os.path.dirname(__file__), "..", "seed_data", "client_contacts.json")
    if not os.path.exists(seed_file):
        return

    db = SessionLocal()
    try:
        crm_count = db.query(Contact).filter(Contact.notes == "From PwC CRM").count()
        if crm_count > 0:
            return

        with open(seed_file) as f:
            records = json.load(f)

        loaded = 0
        for record in records:
            company = db.query(Company).filter(Company.name == record["company_name"]).first()
            if not company:
                continue
            db.add(Contact(
                id=str(_uuid.uuid4()),
                company_id=company.id,
                name=record["name"],
                title=record.get("title"),
                email=record.get("email"),
                relationship_strength=record.get("relationship_strength"),
                notes=record.get("notes", "From PwC CRM"),
            ))
            loaded += 1
        db.commit()
        if loaded:
            print(f"Loaded {loaded} client contacts from seed data.")
    except Exception as e:
        print(f"Client contacts seed loading skipped: {e}")
        db.rollback()
    finally:
        db.close()


def _categorize_uncategorized():
    from app.models.signal import Signal
    db = SessionLocal()
    try:
        renamed = db.query(Signal).filter(Signal.news_category == "competitors").update(
            {"news_category": "company_moves"}, synchronize_session=False,
        )
        if renamed:
            db.commit()
            print(f"Renamed {renamed} 'competitors' categories to 'company_moves'.")

        uncategorized_count = db.query(Signal).filter(Signal.news_category.is_(None)).count()
        if uncategorized_count > 0:
            print(f"Categorizing {uncategorized_count} uncategorized signals...")
            from app.services.signal_categorizer import categorize_uncategorized_signals
            done = categorize_uncategorized_signals(db)
            print(f"Categorized {done} signals.")
    except Exception as e:
        print(f"Signal categorization skipped: {e}")
    finally:
        db.close()


app = FastAPI(
    title="Sales Intelligence Platform",
    description="Signal ingestion and matching for Strategy& partners",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
