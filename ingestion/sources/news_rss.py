import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from ingestion.sources.base import BaseSource, RawSignal
from ingestion.sources.http_client import get as http_get

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

SEARCH_QUERIES = [
    # Automotive
    "automotive industry OR electric vehicle OR EV manufacturing",
    "auto parts supplier OR OEM automotive",
    "General Motors OR Ford OR Stellantis OR Tesla",
    "NHTSA OR vehicle recall OR auto safety",
    # Aerospace & Defense
    "defense contractor OR aerospace industry OR military contract",
    "Lockheed Martin OR Boeing OR Northrop Grumman OR Raytheon",
    "defense budget OR Pentagon OR DoD contract",
    # Energy
    "energy transition OR renewable energy OR clean energy policy",
    "oil gas industry OR LNG OR natural gas pipeline",
    "ExxonMobil OR Chevron OR Shell OR ConocoPhillips",
    "NextEra Energy OR Duke Energy OR Dominion Energy OR Southern Company",
    "FERC OR energy regulation OR grid modernization",
    "hydrogen energy OR carbon capture OR energy storage",
]

SUPPLEMENTAL_FEEDS = [
    ("https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml", "defensenews.com"),
    ("https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=10", "defense.gov"),
    ("https://spacenews.com/feed/", "spacenews.com"),
]


class NewsRSSSource(BaseSource):
    """Aggregates industry news from Google News RSS and trade publication feeds. Free, no key required."""

    def fetch(self, keywords: list[str], max_results: int = 75) -> list[RawSignal]:
        signals = []

        for query in SEARCH_QUERIES:
            url = GOOGLE_NEWS_RSS.format(query=query)
            signals.extend(self._fetch_rss(url, "google_news"))
            if len(signals) >= max_results:
                break

        for feed_url, source_name in SUPPLEMENTAL_FEEDS:
            signals.extend(self._fetch_rss(feed_url, source_name))

        return signals[:max_results]

    def _fetch_rss(self, url: str, default_source: str) -> list[RawSignal]:
        try:
            resp = http_get(url)
            resp.raise_for_status()
        except Exception as e:
            print(f"  RSS fetch failed for {default_source}: {e}")
            return []

        return self._parse_rss(resp.text, default_source)

    def _parse_rss(self, xml_text: str, default_source: str) -> list[RawSignal]:
        signals = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        for item in root.iter("item"):
            title_el = item.find("title")
            link_el = item.find("link")
            pub_date_el = item.find("pubDate")
            desc_el = item.find("description")
            source_el = item.find("source")

            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            if not title:
                continue

            url = link_el.text.strip() if link_el is not None and link_el.text else None
            source_name = source_el.text.strip() if source_el is not None and source_el.text else default_source

            published = None
            if pub_date_el is not None and pub_date_el.text:
                try:
                    published = parsedate_to_datetime(pub_date_el.text)
                    if published.tzinfo is None:
                        published = published.replace(tzinfo=timezone.utc)
                except Exception:
                    pass

            body = None
            if desc_el is not None and desc_el.text:
                body = desc_el.text.strip()[:500]

            signals.append(RawSignal(
                title=title,
                body=body,
                url=url,
                source_name=source_name,
                published_at=published,
            ))

        return signals
