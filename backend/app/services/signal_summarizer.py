from app.models.signal import Signal


TYPE_LABELS = {
    "news": "News",
    "regulatory": "Regulatory",
    "earnings": "Earnings",
    "leadership": "Leadership",
    "ma": "M&A",
    "gov_contract": "Gov Contract",
}


def summarize_signals(signals: list[Signal]) -> dict:
    by_type: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for s in signals:
        t = s.signal_type or "news"
        by_type[t] = by_type.get(t, 0) + 1
        cat = s.news_category or "uncategorized"
        by_category[cat] = by_category.get(cat, 0) + 1
    return {
        "total": len(signals),
        "by_type": by_type,
        "by_category": by_category,
    }


def format_signal_summary(summary: dict) -> str:
    parts = []
    for t in ["regulatory", "ma", "leadership", "earnings", "gov_contract", "news"]:
        count = summary["by_type"].get(t, 0)
        if count > 0:
            parts.append(f"{count} {TYPE_LABELS.get(t, t)}")
    return " · ".join(parts) if parts else f"{summary['total']} signals"
