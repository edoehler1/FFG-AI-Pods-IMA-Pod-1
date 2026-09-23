from ingestion.config import AUTOMOTIVE_KEYWORDS, AEROSPACE_DEFENSE_KEYWORDS, ENERGY_KEYWORDS
from ingestion.sources.base import RawSignal

SIGNAL_TYPES = {
    "regulatory": ["regulation", "rule", "compliance", "NHTSA", "FAA", "EPA", "FERC", "NERC", "DOE", "Federal Register", "proposed rule", "final rule"],
    "earnings": ["earnings", "revenue", "quarterly", "10-K", "10-Q", "annual report", "fiscal", "profit", "loss"],
    "leadership": ["CEO", "CFO", "CTO", "appointed", "resigned", "board of directors", "executive", "hire", "departure"],
    "ma": ["acquisition", "merger", "joint venture", "divest", "spin-off", "buyout", "stake"],
    "gov_contract": ["contract award", "SAM.gov", "DoD contract", "defense contract", "government award", "procurement"],
}

SUB_SECTORS = {
    "automotive": {
        "oem": ["OEM", "automaker", "car manufacturer", "vehicle manufacturer", "General Motors", "GM", "Ford", "Stellantis", "Toyota", "Honda", "Volkswagen", "BMW", "Mercedes", "Hyundai", "Kia", "Nissan"],
        "ev": ["electric vehicle", "EV", "battery electric", "Tesla", "Rivian", "Lucid", "BYD", "EV transition", "EV manufacturing", "charging infrastructure", "battery production", "gigafactory"],
        "tier1_supplier": ["tier 1", "tier one", "auto supplier", "auto parts", "Bosch", "Continental", "Magna", "Aptiv", "Denso", "ZF", "parts supplier", "component supplier"],
        "aftermarket": ["aftermarket", "replacement parts", "auto repair", "service parts", "collision repair"],
    },
    "aerospace_defense": {
        "defense_prime": ["defense prime", "Lockheed Martin", "Northrop Grumman", "General Dynamics", "Raytheon", "RTX", "BAE Systems", "defense contractor", "weapons system", "munitions"],
        "defense_electronics": ["defense electronics", "L3Harris", "Leidos", "radar", "sensor", "electronic warfare", "cybersecurity defense", "C4ISR", "avionics"],
        "commercial_aerospace": ["commercial aerospace", "Boeing", "Airbus", "commercial aircraft", "airline", "aviation", "FAA", "air traffic", "commercial aviation"],
        "space": ["space launch", "satellite", "NASA", "Space Force", "SpaceX", "orbital", "space station", "lunar", "rocket"],
    },
    "energy": {
        "upstream": ["upstream", "exploration", "production", "drilling", "E&P", "oilfield", "shale", "offshore drilling", "ExxonMobil", "Chevron", "ConocoPhillips", "oil production", "well"],
        "midstream": ["midstream", "pipeline", "LNG", "natural gas transport", "Enbridge", "Kinder Morgan", "Williams Companies", "gas processing", "terminal"],
        "downstream": ["downstream", "refinery", "refining", "petrochemical", "fuel", "gasoline", "Shell", "Marathon Petroleum", "Valero", "Phillips 66"],
        "renewables": ["renewable", "solar", "wind power", "wind farm", "clean energy", "NextEra Energy", "green energy", "offshore wind", "onshore wind", "photovoltaic"],
        "utilities": ["utility", "utilities", "power grid", "grid modernization", "Duke Energy", "Dominion Energy", "Southern Company", "AES", "electric utility", "power generation", "smart grid", "distributed energy"],
        "nuclear": ["nuclear energy", "nuclear power", "nuclear reactor", "SMR", "small modular reactor", "uranium", "nuclear plant"],
    },
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


def classify_sub_sector(signal: RawSignal, industry: str | None) -> str | None:
    if not industry or industry not in SUB_SECTORS:
        return None

    text = f"{signal.title} {signal.body or ''}".lower()
    scores = {}
    for sub, keywords in SUB_SECTORS[industry].items():
        scores[sub] = sum(1 for kw in keywords if kw.lower() in text)

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


def classify(signal: RawSignal) -> tuple[str | None, str | None, str]:
    industry = classify_industry(signal)
    sub_sector = classify_sub_sector(signal, industry)
    signal_type = classify_signal_type(signal)
    return industry, sub_sector, signal_type
