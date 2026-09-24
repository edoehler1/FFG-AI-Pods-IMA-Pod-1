import os
from datetime import datetime, timezone

from ingestion.sources.base import BaseSource, RawSignal
from ingestion.sources.http_client import post as http_post

ER_API_URL = "https://eventregistry.org/api/v1/article/getArticles"


class EventRegistrySource(BaseSource):
    """Fetches news articles from Event Registry with entity recognition. Requires EVENT_REGISTRY_API_KEY."""

    def fetch(self, keywords: list[str], max_results: int = 50) -> list[RawSignal]:
        api_key = os.environ.get("EVENT_REGISTRY_API_KEY", "")
        if not api_key:
            print("  Event Registry API key not configured — skipping (set EVENT_REGISTRY_API_KEY in .env)")
            return []

        payload = {
            "action": "getArticles",
            "keyword": keywords[:10],
            "keywordOper": "or",
            "lang": "eng",
            "articlesPage": 1,
            "articlesCount": max_results,
            "articlesSortBy": "date",
            "articlesSortByAsc": False,
            "resultType": "articles",
            "apiKey": api_key,
        }

        try:
            resp = http_post(ER_API_URL, json=payload)
            resp.raise_for_status()
        except Exception as e:
            print(f"  Event Registry fetch failed: {e}")
            return []

        data = resp.json()
        articles = data.get("articles", {}).get("results", [])

        signals = []
        for article in articles:
            title = article.get("title", "").strip()
            if not title:
                continue

            body = (article.get("body") or "")[:500] or None

            source_name = article.get("source", {}).get("title", "event_registry")

            published = None
            date_str = article.get("dateTime") or article.get("date")
            if date_str:
                for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
                    try:
                        published = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                        break
                    except ValueError:
                        continue

            signals.append(RawSignal(
                title=title,
                body=body,
                url=article.get("url"),
                source_name=source_name,
                published_at=published,
            ))

        return signals
