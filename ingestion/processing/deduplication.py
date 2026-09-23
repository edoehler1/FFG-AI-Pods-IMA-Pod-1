import hashlib

from ingestion.sources.base import RawSignal


def compute_dedupe_hash(signal: RawSignal) -> str:
    key = f"{signal.title.lower().strip()}|{signal.source_name}|{signal.published_at}"
    return hashlib.sha256(key.encode()).hexdigest()
