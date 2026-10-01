"""
Migrate data from local SQLite to Supabase PostgreSQL.
Run from project root: python scripts/migrate_to_supabase.py
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine, text, inspect
from app.config import settings


def migrate():
    print(f"Source: data/signals.db")
    print(f"Target: {settings.database_url[:50]}...")
    print()

    sqlite_path = os.path.join(os.path.dirname(__file__), "..", "data", "signals.db")
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    pg_engine = create_engine(settings.database_url)
    pg_inspector = inspect(pg_engine)

    tables = [
        "companies",
        "contacts",
        "engagements",
        "signals",
        "signal_company_matches",
        "company_profiles",
        "weekly_reports",
        "mcp_enrichments",
        "annual_baselines",
    ]

    with pg_engine.connect() as pg_conn:
        for table in tables:
            try:
                pg_columns = set(c["name"] for c in pg_inspector.get_columns(table))
            except Exception:
                print(f"{table}: table not found in PostgreSQL, skipping")
                continue

            try:
                rows = sqlite_conn.execute(f"SELECT * FROM [{table}]").fetchall()
            except Exception:
                print(f"{table}: not found in SQLite, skipping")
                continue

            if not rows:
                print(f"{table}: 0 rows, skipping")
                continue

            existing = pg_conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            if existing > 0:
                print(f"{table}: already has {existing} rows in Supabase, skipping")
                continue

            sqlite_columns = [
                desc[0]
                for desc in sqlite_conn.execute(f"SELECT * FROM [{table}] LIMIT 1").description
            ]
            shared_columns = [c for c in sqlite_columns if c in pg_columns]

            placeholders = ", ".join([f":{c}" for c in shared_columns])
            col_names = ", ".join([f'"{c}"' for c in shared_columns])
            insert_sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"

            inserted = 0
            errors = 0
            for i in range(0, len(rows), 50):
                batch = rows[i : i + 50]
                row_dicts = [{c: dict(row)[c] for c in shared_columns} for row in batch]
                try:
                    pg_conn.execute(text(insert_sql), row_dicts)
                    inserted += len(batch)
                except Exception as e:
                    error_msg = str(e)[:150]
                    print(f"  {table}: error at batch {i}: {error_msg}")
                    pg_conn.rollback()
                    errors += 1
                    if errors > 3:
                        print(f"  {table}: too many errors, stopping")
                        break

            pg_conn.commit()
            print(f"{table}: migrated {inserted}/{len(rows)} rows")

    sqlite_conn.close()
    print("\nDone!")


if __name__ == "__main__":
    migrate()
