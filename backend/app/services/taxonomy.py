import json
from pathlib import Path

_taxonomy = None


def load_taxonomy() -> dict:
    global _taxonomy
    if _taxonomy is None:
        path = Path(__file__).resolve().parent.parent.parent / "seed_data" / "capability_taxonomy.json"
        with open(path) as f:
            _taxonomy = json.load(f)
    return _taxonomy


def get_capabilities_for_sector(industry: str | None) -> str:
    taxonomy = load_taxonomy()
    relevant = []
    for key, group in taxonomy.items():
        if key.startswith("_"):
            continue
        sectors = group.get("sectors", [])
        if not industry or industry in sectors:
            name = group["name"]
            caps = ", ".join(group["capabilities"])
            relevant.append(f"**{name}:** {caps}")
    return "\n".join(relevant)
