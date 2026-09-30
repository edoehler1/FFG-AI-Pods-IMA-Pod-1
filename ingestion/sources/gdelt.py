from datetime import datetime, timezone

from ingestion.sources.base import BaseSource, RawSignal
from ingestion.sources.http_client import get as http_get

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTSource(BaseSource):
    """Fetches news articles from the GDELT Project API. Free, no key required."""

    def fetch(
        self,
        keywords: list[str],
        max_results: int = 50,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[RawSignal]:
        query = " OR ".join(keywords[:10])
        params = {
            "query": query,
            "mode": "ArtList",
            "maxrecords": str(max_results),
            "format": "json",
            "sort": "DateDesc",
        }
        if start_date:
            params["startdatetime"] = start_date.strftime("%Y%m%d%H%M%S")
        if end_date:
            params["enddatetime"] = end_date.strftime("%Y%m%d%H%M%S")

        try:
            resp = http_get(GDELT_DOC_API, params=params)
            resp.raise_for_status()
        except Exception as e:
            print(f"GDELT fetch failed: {e}")
            return []

        data = resp.json()
        articles = data.get("articles", [])

        signals = []
        for article in articles:
            published = None
            if seendate := article.get("seendate"):
                try:
                    published = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            signals.append(RawSignal(
                title=article.get("title", "").strip(),
                body=None,
                url=article.get("url"),
                source_name=article.get("domain", "gdelt"),
                published_at=published,
            ))

        return signals
