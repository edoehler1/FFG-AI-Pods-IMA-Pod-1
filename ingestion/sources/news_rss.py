import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from ingestion.sources.base import BaseSource, RawSignal
from ingestion.sources.http_client import get as http_get

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

FALLBACK_COMPANY_QUERIES = [
    "Ford", "General Motors", "Tesla", "Boeing", "Lockheed Martin",
    "ExxonMobil", "Chevron", "NextEra Energy",
]


SEARCH_NAME_OVERRIDES = {
    "Shell plc": "Shell oil company",
    "Stellantis NV": "Stellantis",
    "Honda Motor Co": "Honda Motor",
    "Lucid Group": "Lucid Motors",
    "Boeing Company": "Boeing",
    "RTX Corporation": "RTX Raytheon",
    "Leidos Holdings": "Leidos",
    "AES Corporation": "AES energy",
    "Southern Company": "Southern Company energy",
    "Enbridge Inc": "Enbridge pipeline",
}


def _get_company_queries() -> list[str]:
    """Pull company names from the database with search-friendly overrides."""
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
        from app.database import SessionLocal
        from app.models.company import Company
        db = SessionLocal()
        companies = db.query(Company.name).all()
        db.close()
        if companies:
            return [SEARCH_NAME_OVERRIDES.get(c.name, c.name) for c in companies]
    except Exception:
        pass
    return FALLBACK_COMPANY_QUERIES

INDUSTRY_QUERIES = [
    # Automotive — regulatory & macro
    "automotive regulation policy 2026",
    "auto tariff trade policy 2026",
    "UAW union automotive labor",
    "NHTSA regulation vehicle safety",
    "emissions standards EPA automotive",
    "EV tax credit incentive policy",
    "CHIPS Act automotive semiconductor",
    "automotive supply chain disruption",
    "electric vehicle manufacturing trends",
    "auto industry tariff impact",
    "semiconductor shortage automotive",
    "autonomous vehicle regulation",
    "automotive workforce manufacturing jobs",
    # Aerospace & Defense — regulatory & macro
    "defense budget NDAA 2026",
    "ITAR export control defense",
    "Pentagon acquisition reform",
    "space policy NASA budget",
    "defense supply chain policy",
    "military spending appropriations 2026",
    "aerospace industry outlook",
    "defense contractor workforce shortage",
    "hypersonic weapons program",
    "defense industrial base policy",
    "FAA aviation safety regulation",
    "NATO defense spending",
    # Energy — regulatory & macro
    "FERC energy regulation 2026",
    "oil price OPEC outlook",
    "Inflation Reduction Act energy",
    "carbon emissions regulation EPA",
    "grid infrastructure investment",
    "LNG export policy",
    "renewable energy subsidy policy",
    "nuclear energy policy regulation",
    "energy transition outlook",
    "utility rate case regulatory",
    "data center energy demand",
    "power grid reliability crisis",
    "energy storage battery policy",
    "natural gas pipeline regulation",
    # Cross-sector macro
    "trade policy tariffs manufacturing 2026",
    "industrial policy manufacturing strategy",
    "supply chain reshoring nearshoring",
    "AI regulation enterprise adoption",
    "SEC corporate governance regulation",
]

SUPPLEMENTAL_FEEDS = [
    ("https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml", "defensenews.com"),
    ("https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=10", "defense.gov"),
    ("https://spacenews.com/feed/", "spacenews.com"),
]


BLOCKED_SOURCE_DOMAINS = {
    "newswirejet.com", "issuewire.com", "menafn.com", "einnews.com",
    "stocktitan.net", "webwire.com", "24-7pressrelease.com",
    "ainews.com", "contentstudio.com", "defenseworld.net",
    "talkmarkets.com", "newsfilecorp.com", "newsfile.com",
}


def _is_blocked_source(source_name: str, url: str | None) -> bool:
    name = source_name.lower().strip()
    if any(d.split(".")[0] in name for d in BLOCKED_SOURCE_DOMAINS):
        return True
    if url:
        url_lower = url.lower()
        for domain in BLOCKED_SOURCE_DOMAINS:
            if domain in url_lower:
                return True
    return False


class NewsRSSSource(BaseSource):
    PER_QUERY_LIMIT = 15

    def fetch(self, keywords: list[str], max_results: int = 1000) -> list[RawSignal]:
        signals = []
        seen_titles = set()

        company_queries = _get_company_queries()
        print(f"  Searching news for {len(company_queries)} companies from database")

        for query in company_queries:
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

            if _is_blocked_source(source_name, url):
                continue

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
