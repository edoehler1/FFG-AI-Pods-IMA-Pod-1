"""
Auto-onboarding: when a company is added, fetch its news, SEC filings, and generate a profile.
"""

import re
import sys
import os

from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.models.company import Company
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch


FILING_TARGETS = {
    "10-K": 3,
    "10-Q": 4,
    "8-K": 5,
    "DEF 14A": 2,
}

SHORT_NAMES_FOR_MATCHING = {
    "Ford Motor Company": ["Ford"], "General Motors": ["GM"], "Tesla Inc": ["Tesla"],
    "Honda Motor Co": ["Honda"], "Rivian Automotive": ["Rivian"], "Lucid Group": ["Lucid"],
    "Stellantis NV": ["Stellantis"], "Aptiv": ["Aptiv"], "Magna International": ["Magna"],
    "Lockheed Martin": ["Lockheed"], "Boeing Company": ["Boeing"],
    "RTX Corporation": ["RTX", "Raytheon"], "Northrop Grumman": ["Northrop"],
    "General Dynamics": ["General Dynamics"], "L3Harris Technologies": ["L3Harris"],
    "Leidos Holdings": ["Leidos"], "ExxonMobil": ["Exxon", "ExxonMobil"],
    "Chevron Corporation": ["Chevron"], "Shell plc": ["Shell"],
    "ConocoPhillips": ["ConocoPhillips"], "NextEra Energy": ["NextEra"],
    "Duke Energy": ["Duke Energy"], "Dominion Energy": ["Dominion Energy"],
    "Southern Company": ["Southern Company"], "AES Corporation": ["AES"],
    "Enbridge Inc": ["Enbridge"],
}


def onboard_company(db: Session, company: Company) -> dict:
    results = {"news_fetched": 0, "filings_fetched": 0, "matches_created": 0, "profile": False}

    news_count = _fetch_news_for_company(db, company)
    results["news_fetched"] = news_count

    filings_count = _fetch_filings_for_company(db, company)
    results["filings_fetched"] = filings_count

    match_count = _run_name_matcher_for_company(db, company)
    results["matches_created"] = match_count

    try:
        from app.services.profile_builder import build_company_profile
        build_company_profile(db, company)
        results["profile"] = True
    except Exception as e:
        print(f"  Profile generation failed: {e}")

    return results


def _fetch_news_for_company(db: Session, company: Company) -> int:
    from ingestion.sources.news_rss import NewsRSSSource, GOOGLE_NEWS_RSS, _normalize_title
    from ingestion.sources.http_client import get as http_get
    from ingestion.processing.deduplication import compute_dedupe_hash
    from ingestion.processing.classifier import classify
    import xml.etree.ElementTree as ET
    from ingestion.sources.base import RawSignal
    import html as html_lib
    from email.utils import parsedate_to_datetime
    from datetime import timezone

    query = company.name.split(" ")[0] if len(company.name.split(" ")) > 2 else company.name
    url = GOOGLE_NEWS_RSS.format(query=query)

    try:
        resp = http_get(url)
        resp.raise_for_status()
    except Exception as e:
        print(f"  News fetch failed for {company.name}: {e}")
        return 0

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        return 0

    new_count = 0
    for item in root.iter("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pub_date_el = item.find("pubDate")
        desc_el = item.find("description")
        source_el = item.find("source")

        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        if not title:
            continue

        url_val = link_el.text.strip() if link_el is not None and link_el.text else None
        source_name = source_el.text.strip() if source_el is not None and source_el.text else "google_news"

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
            clean = html_lib.unescape(clean).strip()
            if clean and not clean.startswith('http'):
                body = clean[:500]

        raw_signal = RawSignal(title=title, body=body, url=url_val, source_name=source_name, published_at=published)
        dedupe_hash = compute_dedupe_hash(raw_signal)

        existing = db.query(Signal).filter(Signal.dedupe_hash == dedupe_hash).first()
        if existing:
            continue

        industry, sub_sector, signal_type = classify(raw_signal)
        signal = Signal(
            title=title, body=body, url=url_val, source_name=source_name,
            published_at=published, industry=industry, sub_sector=sub_sector,
            signal_type=signal_type, dedupe_hash=dedupe_hash,
        )
        db.add(signal)
        new_count += 1

        if new_count >= 15:
            break

    db.commit()
    return new_count


def _fetch_filings_for_company(db: Session, company: Company) -> int:
    from ingestion.sources.http_client import get as http_get
    from ingestion.processing.deduplication import compute_dedupe_hash
    from ingestion.processing.classifier import classify
    from ingestion.sources.base import RawSignal
    from datetime import datetime, timezone

    cik = _lookup_cik(company.name)
    if not cik:
        return 0

    headers = {"User-Agent": "SalesIntelligencePlatform/0.1 (ai-pod-project@pwc.com)"}
    try:
        resp = http_get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=headers)
        resp.raise_for_status()
    except Exception as e:
        print(f"  SEC fetch failed for {company.name}: {e}")
        return 0

    data = resp.json()
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    descriptions = recent.get("primaryDocDescription", [])

    counts: dict[str, int] = {}
    new_count = 0

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

        raw = RawSignal(
            title=f"{company.name} — {form_type} filing",
            body=desc or None,
            url=filing_url,
            source_name="sec_edgar",
            published_at=filed_at,
        )
        dedupe_hash = compute_dedupe_hash(raw)

        existing = db.query(Signal).filter(Signal.dedupe_hash == dedupe_hash).first()
        if existing:
            counts[form_type] = counts.get(form_type, 0) + 1
            continue

        industry, sub_sector, signal_type = classify(raw)
        signal = Signal(
            title=raw.title, body=raw.body, url=filing_url, source_name="sec_edgar",
            published_at=filed_at, industry=industry, sub_sector=sub_sector,
            signal_type=signal_type, dedupe_hash=dedupe_hash,
        )
        db.add(signal)
        counts[form_type] = counts.get(form_type, 0) + 1
        new_count += 1

    db.commit()
    return new_count


def _run_name_matcher_for_company(db: Session, company: Company) -> int:
    from app.services.relevance_scorer import passes_blocklist, score_articles_with_claude

    terms = SHORT_NAMES_FOR_MATCHING.get(company.name)
    if not terms:
        name = company.name.split()[0] if company.name else company.name
        terms = [company.name, name] if len(name) > 3 else [company.name]

    existing = set(
        r.signal_id for r in
        db.query(SignalCompanyMatch.signal_id).filter(SignalCompanyMatch.company_id == company.id).all()
    )

    signals = db.query(Signal).all()
    sec_matches = []
    news_candidates = []

    for signal in signals:
        if signal.id in existing:
            continue
        text = f"{signal.title} {signal.body or ''}".lower()
        matched = False
        for term in terms:
            if re.search(r"\b" + re.escape(term.lower()) + r"\b", text):
                matched = True
                break
        if not matched:
            continue

        if signal.source_name == "sec_edgar":
            sec_matches.append(signal)
        elif passes_blocklist(signal.title, signal.body, signal.signal_type):
            news_candidates.append(signal)

    new = 0
    for signal in sec_matches:
        db.add(SignalCompanyMatch(
            signal_id=signal.id, company_id=company.id,
            match_type="name", match_score=1.0, match_reason="SEC filing",
        ))
        new += 1

    if news_candidates:
        articles = [
            {"index": i, "title": s.title, "body": s.body, "signal_type": s.signal_type}
            for i, s in enumerate(news_candidates)
        ]
        for batch_start in range(0, len(articles), 15):
            batch = articles[batch_start:batch_start + 15]
            scores = score_articles_with_claude(batch, company.name, company.industry)
            score_map = {r["index"]: r for r in scores}
            for i, signal in enumerate(news_candidates[batch_start:batch_start + 15]):
                result = score_map.get(batch_start + i, {})
                claude_score = result.get("score", 50)
                reason = result.get("reason", "matched")
                if claude_score < 50 or result.get("is_duplicate", False):
                    continue
                db.add(SignalCompanyMatch(
                    signal_id=signal.id, company_id=company.id,
                    match_type="name", match_score=claude_score / 100.0,
                    match_reason=reason,
                ))
                new += 1

    db.commit()
    return new


_CIK_CACHE: dict[str, str | None] = {}


def _lookup_cik(company_name: str) -> str | None:
    from app.services.financial_analyzer import CIK_LOOKUP

    if company_name in CIK_LOOKUP:
        return CIK_LOOKUP[company_name]

    if company_name in _CIK_CACHE:
        return _CIK_CACHE[company_name]

    from ingestion.sources.http_client import get as http_get
    try:
        resp = http_get(
            "https://www.sec.gov/files/company_tickers.json",
            headers={"User-Agent": "SalesIntelPlatform/0.1"},
        )
        data = resp.json()
        name_lower = company_name.lower()
        for entry in data.values():
            if entry.get("title", "").lower().startswith(name_lower[:10]):
                cik = str(entry["cik_str"]).zfill(10)
                _CIK_CACHE[company_name] = cik
                return cik
    except Exception:
        pass

    _CIK_CACHE[company_name] = None
    return None
