import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from ingestion.sources.base import BaseSource, RawSignal
from ingestion.sources.http_client import get as http_get

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

COMPANY_QUERIES = [
    "Ford", "General Motors", "Tesla", "Stellantis", "Rivian",
    "Aptiv", "Magna International",
    "Boeing", "Lockheed Martin", "Northrop Grumman", "RTX Raytheon",
    "General Dynamics", "L3Harris", "Leidos",
    "ExxonMobil", "Chevron", "Shell energy", "ConocoPhillips",
    "NextEra Energy", "Duke Energy", "Dominion Energy", "Enbridge",
]

INDUSTRY_QUERIES = [
    "automotive industry",
    "electric vehicle manufacturing",
    "defense contractor",
    "aerospace industry",
    "defense budget Pentagon",
    "energy transition",
    "oil gas industry",
    "renewable energy policy",
    "NHTSA vehicle recall",
    "FERC energy regulation",
]

SUPPLEMENTAL_FEEDS = [
    ("https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml", "defensenews.com"),
    ("https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=10", "defense.gov"),
    ("https://spacenews.com/feed/", "spacenews.com"),
]


class NewsRSSSource(BaseSource):
    PER_QUERY_LIMIT = 15

    def fetch(self, keywords: list[str], max_results: int = 1000) -> list[RawSignal]:
        signals = []
        seen_titles = set()

        for query in COMPANY_QUERIES:
            url = GOOGLE_NEWS_RSS.format(query=query)
            added = 0
            for s in self._fetch_rss(url, "google_news"):
                if added >= self.PER_QUERY_LIMIT:
                    break
                normalized = _normalize_title(s.title)
                if normalized not in seen_titles:
                    seen_titles.add(normalized)
                    signals.append(s)
                    added += 1

        for query in INDUSTRY_QUERIES:
            url = GOOGLE_NEWS_RSS.format(query=query)
            added = 0
            for s in self._fetch_rss(url, "google_news"):
                if added >= self.PER_QUERY_LIMIT:
                    break
                normalized = _normalize_title(s.title)
                if normalized not in seen_titles:
                    seen_titles.add(normalized)
                    signals.append(s)
                    added += 1

        for feed_url, source_name in SUPPLEMENTAL_FEEDS:
            for s in self._fetch_rss(feed_url, source_name):
                normalized = _normalize_title(s.title)
                if normalized not in seen_titles:
                    seen_titles.add(normalized)
                    signals.append(s)

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
                raw = desc_el.text.strip()
                clean = re.sub(r'<[^>]+>', '', raw).strip()
                clean = html.unescape(clean).strip()
                if clean and not clean.startswith('http'):
                    body = clean[:500]

            signals.append(RawSignal(
                title=title,
                body=body,
                url=url,
                source_name=source_name,
                published_at=published,
            ))

        return signals


def _normalize_title(title: str) -> str:
    """Strip source suffix and normalize for dedup. 'Ford plans X - Reuters' == 'Ford plans X - CNBC'"""
    t = title.strip().lower()
    t = re.sub(r'\s*[-–—|]\s*[a-z0-9\s.&]+$', '', t)
    return t
