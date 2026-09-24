"""
Two-stage relevance filter:
1. Blocklist pre-screen — drops obvious consumer/entertainment content
2. Claude scoring — rates actionability 0-100 and deduplicates same-story articles
"""

import json
import re

from app.services.llm_client import call_llm

CONSUMER_BLOCKLIST = [
    "road test", "test drive", "review:", "best cars", "how to buy",
    "museum", "theatre", "theater", "ranking 20", "comparison test",
    "buyer's guide", "what to know before", "mall ", "vs.", " vs ",
    "top 10", "top 5", "best of", "worst of", "car of the year",
    "most reliable", "cheapest", "which is better", "consumer reports",
    "j.d. power", "car show", "auto show display", "concept car",
    "classic car", "vintage", "barn find", "rarest",
]


def passes_blocklist(title: str, body: str | None, signal_type: str | None) -> bool:
    if signal_type and signal_type != "news":
        return True

    text = f"{title} {body or ''}".lower()
    for term in CONSUMER_BLOCKLIST:
        if term in text:
            return False
    return True


def score_articles_with_claude(
    articles: list[dict],
    company_name: str,
    industry: str | None,
) -> list[dict]:
    """
    Send articles to Claude for relevance scoring and deduplication.
    Each article dict should have: index, title, body, signal_type.
    Returns: [{index, score, reason, is_duplicate}]
    """
    if not articles:
        return []

    articles_text = []
    for a in articles:
        articles_text.append(
            f"{a['index']}. [{a.get('signal_type', 'news')}] {a['title']}"
            + (f"\n   {a['body'][:150]}..." if a.get('body') else "")
        )

    prompt = f"""You are evaluating news articles for a Strategy& consulting partner who covers {company_name} ({industry or 'EFS'} sector).

For each article below, provide:
1. **score** (0-100): How actionable is this for finding consulting opportunities? High scores for: restructuring, strategy shifts, leadership changes, M&A, supply chain issues, regulatory impacts, financial distress, market expansion, digital transformation. Low scores for: consumer reviews, entertainment, historical pieces, general interest.
2. **reason**: One sentence explaining the consulting relevance (or why it's irrelevant).
3. **duplicate_of**: If this article covers the same story as another article in this list, put that article's number. Otherwise null.

Articles:
{chr(10).join(articles_text)}

Return ONLY valid JSON array, no markdown. Example:
[{{"index": 1, "score": 85, "reason": "Ford restructuring EV division signals org design opportunity", "duplicate_of": null}}, {{"index": 2, "score": 15, "reason": "Consumer car review, not actionable", "duplicate_of": null}}]"""

    response = call_llm(prompt, max_tokens=2000)
    if not response:
        return [{"index": a["index"], "score": 50, "reason": "Scoring unavailable", "is_duplicate": False} for a in articles]

    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```\w*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        results = json.loads(cleaned)
        scored = []
        for r in results:
            scored.append({
                "index": r.get("index", 0),
                "score": r.get("score", 50),
                "reason": r.get("reason", ""),
                "is_duplicate": r.get("duplicate_of") is not None,
            })
        return scored
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Claude scoring parse error: {e}")
        return [{"index": a["index"], "score": 50, "reason": "Scoring parse error", "is_duplicate": False} for a in articles]
