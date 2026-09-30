"""
Industry News Curator — curates sector-level intelligence shared across all companies in an industry.

Pulls recent industry signals + Federal Register regulatory signals,
deduplicates, then runs Claude to categorize and annotate with partner relevance.
"""

import json
import re
from datetime import datetime, timedelta

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.services.llm_client import call_llm
from app.services.relevance_scorer import passes_blocklist


MAX_RAW_SIGNALS = 80
MAX_CURATED = 20
MIN_IMPORTANCE = 50

VALID_CATEGORIES = {"regulatory", "market", "supply_chain", "labor", "technology"}


def _normalize_for_dedup(title: str) -> str:
    t = title.strip().lower()
    t = re.sub(r'\s*[-–—|]\s*[a-z0-9\s.&]+$', '', t)
    t = re.sub(r'[^a-z0-9\s]', '', t)
    return t[:60]


def _deduplicate_signals(signals: list[Signal]) -> list[Signal]:
    seen: dict[str, Signal] = {}
    for signal in signals:
        key = _normalize_for_dedup(signal.title)
        if key in seen:
            existing = seen[key]
            if len(signal.body or "") > len(existing.body or ""):
                seen[key] = signal
        else:
            seen[key] = signal
    return list(seen.values())


def curate_industry_news(db: Session, industry: str, days_back: int = 7) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    industry_signals = (
        db.query(Signal)
        .filter(
            Signal.industry == industry,
            Signal.source_name != "sec_edgar",
            Signal.published_at >= cutoff,
        )
        .order_by(desc(Signal.published_at))
        .limit(MAX_RAW_SIGNALS)
        .all()
    )

    regulatory_signals = (
        db.query(Signal)
        .filter(
            Signal.published_at >= cutoff,
            or_(
                Signal.signal_type == "regulatory",
                Signal.source_name.like("%federal_register%"),
            ),
        )
        .order_by(desc(Signal.published_at))
        .limit(30)
        .all()
    )

    seen_ids = set()
    all_signals = []
    for s in industry_signals + regulatory_signals:
        if s.id not in seen_ids:
            seen_ids.add(s.id)
            if passes_blocklist(s.title, s.body, s.signal_type, s.source_name, getattr(s, 'url', None)):
                all_signals.append(s)

    deduped = _deduplicate_signals(all_signals)
    if not deduped:
        return []

    return _claude_categorize(deduped, industry)


def _claude_categorize(signals: list[Signal], industry: str) -> list[dict]:
    indexed = []
    for i, signal in enumerate(signals):
        date_str = signal.published_at.strftime("%Y-%m-%d") if signal.published_at else "?"
        body_preview = (signal.body[:200] + "...") if signal.body else ""
        source = signal.source_name or "unknown"
        indexed.append(f"{i}. [{date_str}] [{source}] {signal.title}\n   {body_preview}")

    industry_labels = {
        "automotive": "Automotive",
        "aerospace_defense": "Aerospace & Defense",
        "energy": "Energy, Utilities & Resources",
    }
    label = industry_labels.get(industry, industry)

    prompt = f"""You are curating sector intelligence for Strategy& partners covering the {label} sector.

IMPORTANT: Focus on MACRO and SECTOR-LEVEL signals. Deprioritize articles that are primarily about a single company's earnings, products, or personnel — those belong in Company News, not here. If multiple articles cover the same event, only include the BEST one (mark duplicates with score 0).

Categorize each article AND rate importance (0-100):

Categories:
- REGULATORY: Government regulation, policy changes, agency actions, compliance, trade policy, tariffs
- MARKET: Macro trends, commodity prices, demand shifts, economic indicators, interest rates
- SUPPLY_CHAIN: Supply chain disruptions, logistics, sourcing, materials, semiconductors
- LABOR: Workforce trends, unions, labor market, skills gaps, strikes, workforce transformation
- TECHNOLOGY: Innovation, R&D, digital transformation, emerging tech, industry standards, AI adoption
- SKIP: Not relevant to a partner in this sector, or is company-specific news

For each article scoring 50+:
- index (int)
- category: one of REGULATORY | MARKET | SUPPLY_CHAIN | LABOR | TECHNOLOGY
- score (0-100)
- partner_relevance: one sentence on why a Strategy& partner covering {label} should care

Articles:
{chr(10).join(indexed)}

Return ONLY valid JSON array. Example:
[{{"index": 0, "category": "REGULATORY", "score": 80, "partner_relevance": "..."}}]"""

    response = call_llm(prompt, max_tokens=3000)
    if not response:
        return _fallback_results(signals)

    try:
        cleaned = re.sub(r"```\w*\s*", "", response.strip()).strip()
        results = json.loads(cleaned)
    except (json.JSONDecodeError, KeyError):
        return _fallback_results(signals)

    curated = []
    for r in results:
        idx = r.get("index", -1)
        score = r.get("score", 0)
        category = r.get("category", "").lower()
        if score < MIN_IMPORTANCE or idx < 0 or idx >= len(signals):
            continue
        if category not in VALID_CATEGORIES:
            continue

        signal = signals[idx]
        curated.append({
            "signal": {
                "id": signal.id,
                "title": signal.title,
                "body": signal.body,
                "url": signal.url,
                "source_name": signal.source_name,
                "published_at": signal.published_at.isoformat() if signal.published_at else None,
                "industry": signal.industry,
                "signal_type": signal.signal_type,
            },
            "category": category,
            "importance_score": score,
            "partner_relevance": r.get("partner_relevance", ""),
        })

    curated.sort(key=lambda x: x["importance_score"], reverse=True)
    return curated[:MAX_CURATED]


def _fallback_results(signals: list[Signal]) -> list[dict]:
    results = []
    for signal in signals[:MAX_CURATED]:
        results.append({
            "signal": {
                "id": signal.id,
                "title": signal.title,
                "body": signal.body,
                "url": signal.url,
                "source_name": signal.source_name,
                "published_at": signal.published_at.isoformat() if signal.published_at else None,
                "industry": signal.industry,
                "signal_type": signal.signal_type,
            },
            "category": "market",
            "importance_score": 50,
            "partner_relevance": "Claude curation unavailable — raw signal shown.",
        })
    return results
