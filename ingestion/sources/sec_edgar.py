from datetime import datetime, timezone

from ingestion.sources.base import BaseSource, RawSignal
from ingestion.sources.http_client import get as http_get

DATA_SEC_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

# Target companies in automotive and aerospace/defense (CIK numbers, zero-padded to 10 digits)
TARGET_COMPANIES = {
    # Automotive
    "0000037996": "Ford Motor Company",
    "0001467858": "General Motors",
    "0001318605": "Tesla Inc",
    "0000049196": "Honda Motor Co",
    "0001521332": "Rivian Automotive",
    "0001811210": "Lucid Group",
    "0000789019": "Stellantis NV",
    # Aerospace & Defense
    "0000936468": "Lockheed Martin",
    "0000012927": "Boeing Company",
    "0000101829": "RTX Corporation",
    "0001133421": "Northrop Grumman",
    "0000040533": "General Dynamics",
    "0001047122": "L3Harris Technologies",
    "0001336920": "Leidos Holdings",
}

HEADERS = {"User-Agent": "SalesIntelligencePlatform/0.1 (ai-pod-project@pwc.com)"}


class SECEdgarSource(BaseSource):
    """Fetches recent SEC filings via the data.sec.gov REST API. Free, no key required."""

    def fetch(self, keywords: list[str], max_results: int = 50) -> list[RawSignal]:
        signals = []

        for cik, company_name in TARGET_COMPANIES.items():
            if len(signals) >= max_results:
                break

            try:
                url = DATA_SEC_URL.format(cik=cik)
                resp = http_get(url, headers=HEADERS)
                resp.raise_for_status()
            except Exception as e:
                print(f"  SEC EDGAR failed for {company_name}: {e}")
                continue

            data = resp.json()
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            primary_docs = recent.get("primaryDocument", [])
            descriptions = recent.get("primaryDocDescription", [])

            for i in range(min(5, len(forms))):
                form_type = forms[i] if i < len(forms) else ""
                if form_type not in ("8-K", "10-K", "10-Q", "S-1", "DEF 14A", "4"):
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

        return signals[:max_results]
