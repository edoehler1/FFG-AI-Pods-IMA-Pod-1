import hashlib
import re

from ingestion.sources.base import RawSignal


def _normalize_title(title: str) -> str:
    """Strip source suffix and normalize for dedup."""
    t = title.strip().lower()
    t = re.sub(r'\s*[-–—|]\s*[a-z0-9\s.&]+$', '', t)
    return t


def compute_dedupe_hash(signal: RawSignal) -> str:
    normalized = _normalize_title(signal.title)
    date_part = ""
    if signal.published_at:
        date_part = signal.published_at.strftime("%Y-%m-%d")
    key = f"{normalized}|{date_part}"
    return hashlib.sha256(key.encode()).hexdigest()
