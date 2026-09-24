import os
import sys
from datetime import datetime, timezone

from ingestion.sources.base import BaseSource, RawSignal
from ingestion.sources.http_client import get as http_get

DATA_SEC_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
HEADERS = {"User-Agent": "SalesIntelligencePlatform/0.1 (ai-pod-project@pwc.com)"}

# How many of each filing type to keep per company
FILING_TARGETS = {
    "10-K": 3,
    "10-K/A": 1,
    "10-Q": 4,
    "10-Q/A": 1,
    "8-K": 5,
    "DEF 14A": 2,
}

# Hardcoded CIKs as fallback
KNOWN_CIKS = {
    "Ford Motor Company": "0000037996",
    "General Motors": "0001467858",
    "Tesla Inc": "0001318605",
    "Honda Motor Co": "0000049196",
    "Rivian Automotive": "0001874178",
    "Lucid Group": "0001811210",
    "Stellantis NV": "0000789019",
    "Aptiv": "0001521332",
    "Magna International": "0000749098",
    "Lockheed Martin": "0000936468",
    "Boeing Company": "0000012927",
    "RTX Corporation": "0000101829",
    "Northrop Grumman": "0001133421",
    "General Dynamics": "0000040533",
    "L3Harris Technologies": "0001047122",
    "Leidos Holdings": "0001336920",
    "ExxonMobil": "0000034088",
    "Chevron Corporation": "0000093410",
    "Shell plc": "0001764925",
    "ConocoPhillips": "0001163165",
    "NextEra Energy": "0000753308",
    "Duke Energy": "0000017797",
    "Dominion Energy": "0000715957",
    "Southern Company": "0000092122",
    "AES Corporation": "0000895421",
    "Enbridge Inc": "0000895728",
}


def _get_target_companies() -> dict[str, str]:
    """Pull company names from DB and map to CIKs. Falls back to hardcoded list."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
        from app.database import SessionLocal
        from app.models.company import Company
        db = SessionLocal()
        companies = db.query(Company.name).all()
        db.close()
        if companies:
            result = {}
            for (name,) in companies:
                cik = KNOWN_CIKS.get(name)
                if cik:
                    result[cik] = name
                else:
                    looked_up = _lookup_cik(name)
                    if looked_up:
                        result[looked_up] = name
            return result
    except Exception:
        pass
    return {v: k for k, v in KNOWN_CIKS.items()}


def _lookup_cik(company_name: str) -> str | None:
    try:
        resp = http_get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=HEADERS,
        )
        data = resp.json()
        name_lower = company_name.lower()
        for entry in data.values():
            if entry.get("title", "").lower().startswith(name_lower[:10]):
                return str(entry["cik_str"]).zfill(10)
    except Exception:
        pass
    return None


class SECEdgarSource(BaseSource):
    """Fetches SEC filings with guaranteed counts per filing type."""

    def fetch(self, keywords: list[str], max_results: int = 5000) -> list[RawSignal]:
        target_companies = _get_target_companies()
        print(f"  Fetching filings for {len(target_companies)} companies from database")

        signals = []
        for cik, company_name in target_companies.items():
            company_signals = self._fetch_company(cik, company_name)
            signals.extend(company_signals)

        return signals

    def _fetch_company(self, cik: str, company_name: str) -> list[RawSignal]:
        try:
            resp = http_get(DATA_SEC_URL.format(cik=cik), headers=HEADERS)
            resp.raise_for_status()
        except Exception as e:
            print(f"  SEC EDGAR failed for {company_name}: {e}")
            return []

        data = resp.json()
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        descriptions = recent.get("primaryDocDescription", [])

        counts: dict[str, int] = {}
        signals = []

        for i in range(len(forms)):
            form_type = forms[i]
            target = FILING_TARGETS.get(form_type)
            if target is None:
                continue
            if counts.get(form_type, 0) >= target:
                continue

            filed_at = None
            if i < len(dates) and dates[i]:
                try:
                    filed_at = datetime.strptime(dates[i], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            accession = accessions[i].replace("-", "") if i < len(accessions) else ""
            doc = primary_docs[i] if i < len(primary_docs) else ""
            desc = descriptions[i] if i < len(descriptions) else ""

            filing_url = None
            if accession and doc:
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession}/{doc}"

            signals.append(RawSignal(
                title=f"{company_name} — {form_type} filing",
                body=desc if desc else None,
                url=filing_url,
                source_name="sec_edgar",
                published_at=filed_at,
            ))
            counts[form_type] = counts.get(form_type, 0) + 1

        return signals
