"""Fix remaining migration issues: company_profiles and weekly_reports."""
import sqlite3, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine, text, inspect
from app.config import settings

sqlite_conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "..", "data", "signals.db"))
sqlite_conn.row_factory = sqlite3.Row
pg_engine = create_engine(settings.database_url)
pg_inspector = inspect(pg_engine)

with pg_engine.connect() as pg:
    # company_profiles: FK issue — some company_ids don't exist in PG companies table
    pg_company_ids = set(r[0] for r in pg.execute(text("SELECT id FROM companies")).fetchall())

    rows = sqlite_conn.execute("SELECT * FROM company_profiles").fetchall()
    pg_cols = set(c["name"] for c in pg_inspector.get_columns("company_profiles"))
    sqlite_cols = [d[0] for d in sqlite_conn.execute("SELECT * FROM company_profiles LIMIT 1").description]
    shared = [c for c in sqlite_cols if c in pg_cols]

    existing = pg.execute(text("SELECT COUNT(*) FROM company_profiles")).scalar()
    if existing == 0:
        inserted = 0
        for row in rows:
            d = {c: dict(row)[c] for c in shared}
            if d.get("company_id") not in pg_company_ids:
                continue
            placeholders = ", ".join([f":{c}" for c in shared])
            col_names = ", ".join([f'"{c}"' for c in shared])
            try:
                pg.execute(text(f"INSERT INTO company_profiles ({col_names}) VALUES ({placeholders})"), d)
                inserted += 1
            except Exception as e:
                print(f"  company_profiles skip: {str(e)[:100]}")
        pg.commit()
        print(f"company_profiles: migrated {inserted}/{len(rows)}")
    else:
        print(f"company_profiles: already has {existing} rows")

    # weekly_reports: has_opportunity is integer in SQLite but boolean in PG
    rows = sqlite_conn.execute("SELECT * FROM weekly_reports").fetchall()
    pg_cols = set(c["name"] for c in pg_inspector.get_columns("weekly_reports"))
    sqlite_cols = [d[0] for d in sqlite_conn.execute("SELECT * FROM weekly_reports LIMIT 1").description]
    shared = [c for c in sqlite_cols if c in pg_cols]

    existing = pg.execute(text("SELECT COUNT(*) FROM weekly_reports")).scalar()
    if existing == 0:
        inserted = 0
        for row in rows:
            d = {c: dict(row)[c] for c in shared}
            if d.get("company_id") not in pg_company_ids:
                continue
            if "has_opportunity" in d and d["has_opportunity"] is not None:
                d["has_opportunity"] = bool(d["has_opportunity"])
            placeholders = ", ".join([f":{c}" for c in shared])
            col_names = ", ".join([f'"{c}"' for c in shared])
            try:
                pg.execute(text(f"INSERT INTO weekly_reports ({col_names}) VALUES ({placeholders})"), d)
                inserted += 1
            except Exception as e:
                print(f"  weekly_reports skip: {str(e)[:100]}")
        pg.commit()
        print(f"weekly_reports: migrated {inserted}/{len(rows)}")
    else:
        print(f"weekly_reports: already has {existing} rows")

sqlite_conn.close()
print("Done!")
