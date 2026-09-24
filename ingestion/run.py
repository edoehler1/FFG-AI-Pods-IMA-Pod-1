"""
CLI runner for signal ingestion.

Usage:
    python -m ingestion.run                     # Run all sources
    python -m ingestion.run --source news       # Run one source
    python -m ingestion.run --source sec_edgar
    python -m ingestion.run --source federal_register
    python -m ingestion.run --source gdelt
    python -m ingestion.run --source sam_gov
    python -m ingestion.run --source usaspending
    python -m ingestion.run --source event_registry
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ingestion.config import DATABASE_URL, ALL_KEYWORDS, GOV_CONTRACT_KEYWORDS
from ingestion.sources.news_rss import NewsRSSSource
from ingestion.sources.sec_edgar import SECEdgarSource
from ingestion.sources.federal_register import FederalRegisterSource
from ingestion.sources.gdelt import GDELTSource
from ingestion.sources.sam_gov import SAMGovSource
from ingestion.sources.usaspending import USASpendingSource
from ingestion.sources.event_registry import EventRegistrySource
from ingestion.processing.deduplication import compute_dedupe_hash
from ingestion.processing.classifier import classify

from app.database import Base
from app.models.signal import Signal


SOURCES = {
    "news": (NewsRSSSource, []),
    "sec_edgar": (SECEdgarSource, []),
    "federal_register": (FederalRegisterSource, ["automotive", "vehicle", "defense", "aerospace", "aviation"]),
    "gdelt": (GDELTSource, ALL_KEYWORDS[:10]),
    "sam_gov": (SAMGovSource, GOV_CONTRACT_KEYWORDS),
    "usaspending": (USASpendingSource, GOV_CONTRACT_KEYWORDS),
    "event_registry": (EventRegistrySource, ALL_KEYWORDS[:10]),
}


def run_ingestion(source_names: list[str] | None = None):
    connect_args = {}
    if DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        os.makedirs("data", exist_ok=True)

    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    targets = source_names or list(SOURCES.keys())
    total_new = 0

    for name in targets:
        if name not in SOURCES:
            print(f"Unknown source: {name}. Available: {', '.join(SOURCES.keys())}")
            continue

        source_class, keywords = SOURCES[name]
        source = source_class()

        print(f"\nFetching from {name}...")
        raw_signals = source.fetch(keywords=keywords)
        print(f"  Got {len(raw_signals)} raw signals")

        session = Session()
        new_count = 0

        for raw in raw_signals:
            if not raw.title:
                continue

            dedupe_hash = compute_dedupe_hash(raw)
            existing = session.query(Signal).filter(Signal.dedupe_hash == dedupe_hash).first()
            if existing:
                continue

            industry, sub_sector, signal_type = classify(raw)

            signal = Signal(
                title=raw.title,
                body=raw.body,
                url=raw.url,
                source_name=raw.source_name,
                published_at=raw.published_at,
                industry=industry,
                sub_sector=sub_sector,
                signal_type=signal_type,
                dedupe_hash=dedupe_hash,
            )
            session.add(signal)
            new_count += 1

        session.commit()
        session.close()
        print(f"  Stored {new_count} new signals (skipped {len(raw_signals) - new_count} duplicates)")
        total_new += new_count

    print(f"\nDone. {total_new} new signals ingested total.")


def main():
    parser = argparse.ArgumentParser(description="Run signal ingestion")
    parser.add_argument("--source", type=str,
        help="Specific source to run (news, sec_edgar, federal_register, gdelt, sam_gov, usaspending, event_registry)")
    args = parser.parse_args()

    sources = [args.source] if args.source else None
    run_ingestion(sources)


if __name__ == "__main__":
    main()
