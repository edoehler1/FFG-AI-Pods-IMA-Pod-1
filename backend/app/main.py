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
    _categorize_uncategorized()
    yield


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
