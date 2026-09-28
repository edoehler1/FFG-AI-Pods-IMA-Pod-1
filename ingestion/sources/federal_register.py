from datetime import datetime, timezone

from ingestion.sources.base import BaseSource, RawSignal
from ingestion.sources.http_client import get as http_get

FR_API = "https://www.federalregister.gov/api/v1/documents.json"


class FederalRegisterSource(BaseSource):
    """Fetches regulatory documents from the Federal Register API. Free, no key required."""

    def fetch(self, keywords: list[str], max_results: int = 20) -> list[RawSignal]:
        params = {
            "per_page": str(max_results),
            "order": "newest",
            "conditions[term]": " ".join(keywords[:5]),
            "conditions[agencies][]": [
                "national-highway-traffic-safety-administration",
                "federal-aviation-administration",
                "defense-department",
                "environmental-protection-agency",
                "federal-energy-regulatory-commission",
                "energy-department",
                "nuclear-regulatory-commission",
            ],
        }

        try:
            resp = http_get(FR_API, params=params)
            resp.raise_for_status()
        except Exception as e:
            print(f"Federal Register fetch failed: {e}")
            return []

        data = resp.json()
        results = data.get("results", [])

        signals = []
        for doc in results:
            published = None
            if pub_date := doc.get("publication_date"):
                try:
                    published = datetime.strptime(pub_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            signals.append(RawSignal(
                title=doc.get("title", "").strip(),
                body=doc.get("abstract"),
                url=doc.get("html_url"),
                source_name="federal_register",
                published_at=published,
            ))

        return signals
