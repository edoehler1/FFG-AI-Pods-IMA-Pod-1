"""
Batch-categorizes signals into: regulatory, macro, company_moves, trends, general.
Stores the category on the signal itself so it's fast to query.
"""

import json
import re

from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.services.llm_client import call_llm, is_llm_available

CATEGORIES = ["regulatory", "macro", "company_moves", "trends", "general"]


def categorize_uncategorized_signals(db: Session, batch_size: int = 20, max_batches: int = 50) -> int:
    uncategorized = (
        db.query(Signal)
        .filter(Signal.news_category == None, Signal.source_name != "sec_edgar")
        .limit(batch_size * max_batches)
        .all()
    )

    if not uncategorized:
        return 0

    if not is_llm_available():
        for s in uncategorized:
            s.news_category = _keyword_categorize(s)
        db.commit()
        return len(uncategorized)

    total = 0
    for i in range(0, len(uncategorized), batch_size):
        batch = uncategorized[i:i + batch_size]
        articles = []
        for j, s in enumerate(batch):
            articles.append(f"{j}. [{s.signal_type}] {s.title}")

        prompt = f"""Categorize each article into one of: regulatory, macro, company_moves, trends, general.

- "regulatory" — regulation, policy, government action, compliance, agency rules
- "macro" — tariffs, trade, economic trends, supply chain disruptions, labor, interest rates, geopolitics
- "company_moves" — specific company actions: earnings, M&A, restructuring, leadership changes, partnerships, contract wins. Note: companies in the same industry are NOT necessarily competitors — an OEM and its supplier are value chain partners, not competitors.
- "trends" — technology shifts, industry outlook, innovation, emerging themes
- "general" — doesn't fit the above

Articles:
{chr(10).join(articles)}

Return ONLY a JSON array: [{{"index": 0, "category": "regulatory"}}, ...]"""

        response = call_llm(prompt, max_tokens=1000)
        if not response:
            for s in batch:
                s.news_category = _keyword_categorize(s)
            total += len(batch)
            continue

        try:
            cleaned = re.sub(r"```\w*\s*", "", response).strip()
            json_match = re.search(r'\[.*\]', cleaned, re.DOTALL)
            if json_match:
                results = json.loads(json_match.group())
                result_map = {r["index"]: r["category"] for r in results if "index" in r and "category" in r}
                for j, s in enumerate(batch):
                    cat = result_map.get(j, _keyword_categorize(s))
                    s.news_category = cat if cat in CATEGORIES else "general"
                    total += 1
            else:
                for s in batch:
                    s.news_category = _keyword_categorize(s)
                    total += 1
        except Exception:
            for s in batch:
                s.news_category = _keyword_categorize(s)
                total += 1

        db.commit()

    # SEC filings are always regulatory
    sec_uncategorized = db.query(Signal).filter(Signal.news_category == None, Signal.source_name == "sec_edgar").all()
    for s in sec_uncategorized:
        s.news_category = "regulatory"
    db.commit()
    total += len(sec_uncategorized)

    # USASpending contract line items are not useful for consulting
    usa_spending = db.query(Signal).filter(Signal.source_name == "usaspending", Signal.news_category != "general").all()
    for s in usa_spending:
        s.news_category = "general"
    db.commit()
    total += len(usa_spending)

    return total


def _keyword_categorize(signal) -> str:
    text = f"{signal.title} {signal.body or ''}".lower()
    reg_words = ["regulation", "rule", "compliance", "epa", "nhtsa", "faa", "ferc", "policy", "legislation", "act", "bill"]
    macro_words = ["tariff", "trade", "supply chain", "labor", "union", "interest rate", "inflation", "gdp", "opec", "sanction"]
    company_words = ["earnings", "revenue", "stock", "acquisition", "merger", "ceo", "quarterly", "market share", "partnership", "restructuring", "layoff"]
    trend_words = ["trend", "outlook", "forecast", "emerging", "innovation", "ai", "autonomous", "hydrogen", "transition"]

    scores = {
        "regulatory": sum(1 for w in reg_words if w in text),
        "macro": sum(1 for w in macro_words if w in text),
        "company_moves": sum(1 for w in company_words if w in text),
        "trends": sum(1 for w in trend_words if w in text),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"
