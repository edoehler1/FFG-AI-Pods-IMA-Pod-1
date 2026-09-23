from ingestion.config import AUTOMOTIVE_KEYWORDS, AEROSPACE_DEFENSE_KEYWORDS, ENERGY_KEYWORDS
from ingestion.sources.base import RawSignal

SIGNAL_TYPES = {
    "regulatory": ["regulation", "rule", "compliance", "NHTSA", "FAA", "EPA", "ITAR", "EAR", "FERC", "NERC", "DOE", "Federal Register", "proposed rule", "final rule"],
    "earnings": ["earnings", "revenue", "quarterly", "10-K", "10-Q", "annual report", "fiscal", "profit", "loss"],
    "leadership": ["CEO", "CFO", "CTO", "appointed", "resigned", "board of directors", "executive", "hire", "departure"],
    "ma": ["acquisition", "merger", "joint venture", "divest", "spin-off", "buyout", "stake"],
    "gov_contract": ["contract award", "SAM.gov", "DoD contract", "defense contract", "government award", "procurement"],
}


def classify_industry(signal: RawSignal) -> str | None:
    text = f"{signal.title} {signal.body or ''}".lower()
    scores = {
        "automotive": sum(1 for kw in AUTOMOTIVE_KEYWORDS if kw.lower() in text),
        "aerospace_defense": sum(1 for kw in AEROSPACE_DEFENSE_KEYWORDS if kw.lower() in text),
        "energy": sum(1 for kw in ENERGY_KEYWORDS if kw.lower() in text),
    }

    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    return None


def classify_signal_type(signal: RawSignal) -> str:
    text = f"{signal.title} {signal.body or ''}".lower()

    best_type = "news"
    best_score = 0
    for sig_type, keywords in SIGNAL_TYPES.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > best_score:
            best_score = score
            best_type = sig_type

    return best_type


def classify(signal: RawSignal) -> tuple[str | None, str]:
    return classify_industry(signal), classify_signal_type(signal)
