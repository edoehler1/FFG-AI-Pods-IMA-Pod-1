"""
Historical News Fetcher — pulls 12 months of news for a company via GDELT + Google News RSS,
then runs a two-pass Claude filter for relevance and strategic importance.
"""

import json
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.services.llm_client import call_llm
from app.services.relevance_scorer import passes_blocklist

SEARCH_NAME_OVERRIDES = {
    "Shell plc": "Shell oil company",
    "Stellantis NV": "Stellantis",
    "Boeing Company": "Boeing",
    "RTX Corporation": "RTX Raytheon",
    "Leidos Holdings": "Leidos",
    "AES Corporation": "AES energy",
    "Southern Company": "Southern Company energy",
    "Enbridge Inc": "Enbridge pipeline",
    "L3Harris Technologies": "L3Harris",
    "Duke Energy": "Duke Energy utility",
    "Magna International": "Magna auto supplier",
}

QUARTERS_BACK = 4
GDELT_PER_QUARTER = 75
RSS_PER_QUERY = 50

STRATEGIC_QUERIES = [
    "{company} restructuring",
    "{company} acquisition OR merger OR divestiture",
    "{company} CEO OR CFO OR leadership",
    "{company} earnings OR revenue OR profit",
    "{company} contract OR deal OR partnership",
    "{company} regulatory OR compliance OR lawsuit",
    "{company} strategy OR transformation",
]


def _get_search_terms(company_name: str) -> list[str]:
    override = SEARCH_NAME_OVERRIDES.get(company_name)
    if override:
        return [override, company_name]
    short = company_name.split()[0] if len(company_name.split()) > 2 else company_name
    return [company_name, short] if short != company_name else [company_name]


def _fetch_gdelt_historical(company_name: str, start: datetime, end: datetime) -> list[dict]:
    from ingestion.sources.gdelt import GDELTSource

    terms = _get_search_terms(company_name)
    source = GDELTSource()
    try:
        raw_signals = source.fetch(terms, max_results=GDELT_PER_QUARTER, start_date=start, end_date=end)
    except Exception as e:
        print(f"  GDELT fetch error: {e}")
        return []

    articles = []
    for s in raw_signals:
        if not s.title or len(s.title) < 10:
            continue
        if not passes_blocklist(s.title, s.body, None, s.source_name, s.url):
            continue
        articles.append({
            "title": s.title,
            "body": s.body,
            "url": s.url,
            "source_name": s.source_name,
            "published_at": s.published_at,
        })
    return articles


def _fetch_rss_broad(company_name: str) -> list[dict]:
    from ingestion.sources.news_rss import GOOGLE_NEWS_RSS, NewsRSSSource

    source = NewsRSSSource()
    all_articles = []
    terms = _get_search_terms(company_name)

    for term in terms:
        url = GOOGLE_NEWS_RSS.format(query=term)
        raw = source._fetch_rss(url, "google_news")
        for s in raw[:RSS_PER_QUERY]:
            if not s.title or len(s.title) < 10:
                continue
            if not passes_blocklist(s.title, s.body, None, s.source_name, s.url):
                continue
            all_articles.append({
                "title": s.title,
                "body": s.body,
                "url": s.url,
                "source_name": s.source_name,
                "published_at": s.published_at,
            })

    for query_template in STRATEGIC_QUERIES:
        query = query_template.format(company=terms[0])
        url = GOOGLE_NEWS_RSS.format(query=query)
        raw = source._fetch_rss(url, "google_news")
        for s in raw[:20]:
            if not s.title or len(s.title) < 10:
                continue
            if not passes_blocklist(s.title, s.body, None, s.source_name, s.url):
                continue
            all_articles.append({
                "title": s.title,
                "body": s.body,
                "url": s.url,
                "source_name": s.source_name,
                "published_at": s.published_at,
            })

    print(f"  RSS broad: {len(all_articles)} articles for {company_name}")
    return all_articles


def _fetch_all_sources(company_name: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    all_articles = []
    seen_titles = set()

    def _add_unique(articles: list[dict]):
        for a in articles:
            normalized = a["title"].strip().lower()[:80]
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                all_articles.append(a)

    for q in range(QUARTERS_BACK):
        end = now - timedelta(days=q * 90)
        start = end - timedelta(days=90)
        print(f"  GDELT: {company_name} {start.strftime('%Y-%m')} to {end.strftime('%Y-%m')}...")
        _add_unique(_fetch_gdelt_historical(company_name, start, end))

    _add_unique(_fetch_rss_broad(company_name))

    print(f"  Total raw pool: {len(all_articles)} unique articles for {company_name}")
    return all_articles


def _claude_relevance_filter(
    articles: list[dict], company_name: str, industry: str | None, batch_size: int = 20,
) -> list[dict]:
    if not articles:
        return []

    surviving = []
    for batch_start in range(0, len(articles), batch_size):
        batch = articles[batch_start:batch_start + batch_size]
        indexed = []
        for i, a in enumerate(batch):
            body_preview = (a["body"][:150] + "...") if a.get("body") else ""
            indexed.append(f"{i}. {a['title']}\n   {body_preview}")

        prompt = f"""You are filtering news articles for relevance to {company_name} ({industry or 'EFS'} sector).

For each article, determine:
1. Is this ACTUALLY about {company_name}? (not a different company with a similar name, not consumer/lifestyle content, not a passing mention)
2. Score 0-100 for relevance to {company_name}'s business operations and strategy.

Articles:
{chr(10).join(indexed)}

Return ONLY valid JSON array:
[{{"index": 0, "score": 85, "relevant": true}}, {{"index": 1, "score": 20, "relevant": false}}]"""

        response = call_llm(prompt, max_tokens=1500)
        if not response:
            surviving.extend(batch)
            continue

        try:
            cleaned = re.sub(r"```\w*\s*", "", response.strip()).strip()
            results = json.loads(cleaned)
            score_map = {r["index"]: r for r in results}
            for i, article in enumerate(batch):
                result = score_map.get(i, {})
                if result.get("score", 0) >= 60 and result.get("relevant", False):
                    surviving.append(article)
        except (json.JSONDecodeError, KeyError):
            surviving.extend(batch)

    print(f"  Relevance filter: {len(articles)} -> {len(surviving)}")
    return surviving


def _claude_importance_filter(
    articles: list[dict], company_name: str, industry: str | None, batch_size: int = 25,
) -> list[dict]:
    if not articles:
        return []

    surviving = []
    for batch_start in range(0, len(articles), batch_size):
        batch = articles[batch_start:batch_start + batch_size]
        indexed = []
        for i, a in enumerate(batch):
            date_str = a["published_at"].strftime("%Y-%m-%d") if a.get("published_at") else "?"
            body_preview = (a["body"][:150] + "...") if a.get("body") else ""
            indexed.append(f"{i}. [{date_str}] {a['title']}\n   {body_preview}")

        prompt = f"""You are a Strategy& intelligence analyst rating the strategic importance of news about {company_name} ({industry or 'EFS'}).

Rate each article 0-100 for STRATEGIC IMPORTANCE — how significant is this event for understanding the company's trajectory and consulting opportunities?

HIGH importance (70+): M&A, restructuring, CEO/CFO changes, major regulatory actions, billion-dollar contracts, earnings surprises, strategic pivots, activist investor actions, major lawsuits.
MEDIUM importance (50-69): Notable contracts, leadership hires, partnership announcements, supply chain shifts, labor actions.
LOW importance (<50): Minor product updates, routine earnings that match expectations, general industry commentary, analyst upgrades/downgrades, minor personnel changes.

Also tag each: M&A | Leadership | Regulatory | Financial | Operational | Strategic | Contract | Labor | Skip

Articles:
{chr(10).join(indexed)}

Return ONLY valid JSON array:
[{{"index": 0, "score": 85, "tag": "M&A"}}, {{"index": 1, "score": 30, "tag": "Skip"}}]"""

        response = call_llm(prompt, max_tokens=1500)
        if not response:
            surviving.extend(batch)
            continue

        try:
            cleaned = re.sub(r"```\w*\s*", "", response.strip()).strip()
            results = json.loads(cleaned)
            score_map = {r["index"]: r for r in results}
            for i, article in enumerate(batch):
                result = score_map.get(i, {})
                score = result.get("score", 0)
                tag = result.get("tag", "Skip")
                if score >= 50 and tag != "Skip":
                    article["importance_score"] = score
                    article["event_tag"] = tag
                    surviving.append(article)
        except (json.JSONDecodeError, KeyError):
            surviving.extend(batch)

    print(f"  Importance filter: {len(articles)} -> {len(surviving)}")
    return surviving


def fetch_historical_news(db: Session, company_name: str, company_id: str, industry: str | None) -> int:
    from ingestion.processing.deduplication import compute_dedupe_hash
    from ingestion.processing.classifier import classify
    from ingestion.sources.base import RawSignal

    print(f"Fetching 12-month historical news for {company_name}...")
    raw_articles = _fetch_all_sources(company_name)

    relevant = _claude_relevance_filter(raw_articles, company_name, industry)
    important = _claude_importance_filter(relevant, company_name, industry)

    new_count = 0
    new_signal_ids = []

    for article in important:
        raw = RawSignal(
            title=article["title"],
            body=article.get("body"),
            url=article.get("url"),
            source_name=article.get("source_name", "gdelt"),
            published_at=article.get("published_at"),
        )
        dedupe_hash = compute_dedupe_hash(raw)

        existing = db.query(Signal).filter(Signal.dedupe_hash == dedupe_hash).first()
        if existing:
            existing_match = (
                db.query(SignalCompanyMatch)
                .filter(SignalCompanyMatch.signal_id == existing.id, SignalCompanyMatch.company_id == company_id)
                .first()
            )
            if not existing_match:
                db.add(SignalCompanyMatch(
                    signal_id=existing.id,
                    company_id=company_id,
                    match_type="name",
                    match_score=article.get("importance_score", 70) / 100.0,
                    match_reason=article.get("event_tag", "historical"),
                ))
            continue

        sig_industry, sub_sector, signal_type = classify(raw)
        signal = Signal(
            title=raw.title,
            body=raw.body,
            url=raw.url,
            source_name=raw.source_name,
            published_at=raw.published_at,
            industry=sig_industry,
            sub_sector=sub_sector,
            signal_type=signal_type,
            dedupe_hash=dedupe_hash,
        )
        db.add(signal)
        db.flush()

        db.add(SignalCompanyMatch(
            signal_id=signal.id,
            company_id=company_id,
            match_type="name",
            match_score=article.get("importance_score", 70) / 100.0,
            match_reason=article.get("event_tag", "historical"),
        ))
        new_signal_ids.append(signal.id)
        new_count += 1

    db.commit()
    print(f"  Stored {new_count} new signals for {company_name} ({len(important)} total after filtering)")
    return new_count
