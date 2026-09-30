"""
Company News Curator — curates the weekly company-specific news feed.

Pulls recent signals matched to a company, deduplicates same-story articles,
then runs Claude to score importance, generate "why it matters" and
"suggested action" annotations, and tag with strategic category.
"""

import json
import re
from datetime import datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.services.llm_client import call_llm
from app.services.relevance_scorer import passes_blocklist


MAX_RAW_SIGNALS = 50
MAX_CURATED = 20
MIN_IMPORTANCE = 60


def _normalize_for_dedup(title: str) -> str:
    t = title.strip().lower()
    t = re.sub(r'\s*[-–—|]\s*[a-z0-9\s.&]+$', '', t)
    t = re.sub(r'[^a-z0-9\s]', '', t)
    return t[:60]


def _deduplicate_signals(signals: list[tuple[Signal, SignalCompanyMatch]]) -> list[tuple[Signal, SignalCompanyMatch]]:
    seen: dict[str, tuple[Signal, SignalCompanyMatch]] = {}
    for signal, match in signals:
        key = _normalize_for_dedup(signal.title)
        if key in seen:
            existing_signal, existing_match = seen[key]
            existing_body_len = len(existing_signal.body or "")
            new_body_len = len(signal.body or "")
            existing_score = existing_match.match_score or 0
            new_score = match.match_score or 0
            if new_score > existing_score or (new_score == existing_score and new_body_len > existing_body_len):
                seen[key] = (signal, match)
        else:
            seen[key] = (signal, match)
    return list(seen.values())


def curate_company_news(db: Session, company: Company, days_back: int = 7) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    matches = (
        db.query(SignalCompanyMatch)
        .filter(
            SignalCompanyMatch.company_id == company.id,
            SignalCompanyMatch.match_type == "name",
        )
        .all()
    )
    if not matches:
        return []

    signal_ids = [m.signal_id for m in matches]
    match_map = {m.signal_id: m for m in matches}

    signals = (
        db.query(Signal)
        .filter(
            Signal.id.in_(signal_ids),
            Signal.source_name != "sec_edgar",
            Signal.published_at >= cutoff,
        )
        .order_by(desc(Signal.published_at))
        .limit(MAX_RAW_SIGNALS)
        .all()
    )
    if not signals:
        return []

    filtered = [
        (s, match_map[s.id])
        for s in signals
        if passes_blocklist(s.title, s.body, s.signal_type, s.source_name, getattr(s, 'url', None))
    ]

    deduped = _deduplicate_signals(filtered)
    if not deduped:
        return []

    from app.services.taxonomy import get_capabilities_for_sector
    taxonomy = get_capabilities_for_sector(company.industry)

    return _claude_curate(deduped, company, taxonomy)


def _claude_curate(
    signals: list[tuple[Signal, SignalCompanyMatch]],
    company: Company,
    taxonomy: str,
) -> list[dict]:
    indexed = []
    for i, (signal, _match) in enumerate(signals):
        date_str = signal.published_at.strftime("%Y-%m-%d") if signal.published_at else "?"
        body_preview = (signal.body[:200] + "...") if signal.body else ""
        indexed.append(f"{i}. [{date_str}] {signal.title}\n   {body_preview}")

    prompt = f"""You are curating a weekly intelligence briefing for a Strategy& partner covering {company.name} ({company.industry or 'EFS'} sector).

A signal is ONLY worth including if it creates a potential consulting engagement that maps to one of these S& capabilities:

{taxonomy}

EXCLUDE (score 0):
- Earnings call transcripts, earnings summaries, quarterly results recaps
- Analyst upgrades/downgrades, price targets, stock commentary
- General market/stock movement articles
- Consumer product reviews or lifestyle content
- Duplicate articles covering the same event (keep only the best one)

INCLUDE every signal where a partner could ACT — something changed in the business that creates a need for one of the S& capabilities above. No hard cap on how many to return. If 2 are actionable, return 2. If 8 are actionable, return 8. The taxonomy mapping is the filter, not a number.

For each signal worth including:
- index (int)
- score (0-100)
- taxonomy_tag: the EXACT capability name from the taxonomy above
- why_it_matters: one sentence connecting this signal to that specific S& capability
- suggested_action: one concrete sentence on what the partner should do

Articles:
{chr(10).join(indexed)}

Return ONLY valid JSON array. Example:
[{{"index": 0, "score": 85, "taxonomy_tag": "Separation & Carve-out", "why_it_matters": "...", "suggested_action": "..."}}]"""

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
        if score < MIN_IMPORTANCE or idx < 0 or idx >= len(signals):
            continue

        signal, match = signals[idx]
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
            "importance_score": score,
            "taxonomy_tag": r.get("taxonomy_tag", ""),
            "why_it_matters": r.get("why_it_matters", ""),
            "suggested_action": r.get("suggested_action", ""),
        })

    curated.sort(key=lambda x: x["importance_score"], reverse=True)
    return curated[:MAX_CURATED]


def _fallback_results(signals: list[tuple[Signal, SignalCompanyMatch]]) -> list[dict]:
    results = []
    for signal, match in signals[:MAX_CURATED]:
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
            "importance_score": 50,
            "taxonomy_tag": "",
            "why_it_matters": "Claude curation unavailable — raw signal shown.",
            "suggested_action": "Review manually.",
        })
    return results
