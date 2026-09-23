from datetime import datetime, timezone

from ingestion.sources.base import BaseSource, RawSignal
from ingestion.sources.http_client import get as http_get

DATA_SEC_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

# Target companies across EFS sectors (CIK numbers, zero-padded to 10 digits)
TARGET_COMPANIES = {
    # Automotive — OEMs
    "0000037996": "Ford Motor Company",
    "0001467858": "General Motors",
    "0001318605": "Tesla Inc",
    "0000049196": "Honda Motor Co",
    "0001874178": "Rivian Automotive",
    "0001811210": "Lucid Group",
    "0000789019": "Stellantis NV",
    # Automotive — Tier 1 Suppliers
    "0001521332": "Aptiv",
    "0000749098": "Magna International",
    # Aerospace & Defense
    "0000936468": "Lockheed Martin",
    "0000012927": "Boeing Company",
    "0000101829": "RTX Corporation",
    "0001133421": "Northrop Grumman",
    "0000040533": "General Dynamics",
    "0001047122": "L3Harris Technologies",
    "0001336920": "Leidos Holdings",
    # Energy
    "0000034088": "ExxonMobil",
    "0000093410": "Chevron Corporation",
    "0001764925": "Shell plc",
    "0001163165": "ConocoPhillips",
    "0000753308": "NextEra Energy",
    "0000017797": "Duke Energy",
    "0000715957": "Dominion Energy",
    "0000092122": "Southern Company",
    "0000895421": "AES Corporation",
    "0000895728": "Enbridge Inc",
}

HEADERS = {"User-Agent": "SalesIntelligencePlatform/0.1 (ai-pod-project@pwc.com)"}


class SECEdgarSource(BaseSource):
    """Fetches recent SEC filings via the data.sec.gov REST API. Free, no key required."""

    RELEVANT_FORMS = {"8-K", "10-K", "10-Q", "10-K/A", "10-Q/A", "DEF 14A"}

    def fetch(self, keywords: list[str], max_results: int = 200) -> list[RawSignal]:
        signals = []

        for cik, company_name in TARGET_COMPANIES.items():
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

            company_count = 0
            for i in range(len(forms)):
                if company_count >= 15:
                    break
                form_type = forms[i] if i < len(forms) else ""
                if form_type not in self.RELEVANT_FORMS:
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
                company_count += 1

        return signals[:max_results]
