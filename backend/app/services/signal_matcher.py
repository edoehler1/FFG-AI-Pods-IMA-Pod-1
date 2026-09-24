import json
import re
from collections import namedtuple

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.signal import Signal
from app.models.signal_company import SignalCompanyMatch
from app.services.llm_client import call_llm, is_llm_available
from app.services.taxonomy import get_capabilities_for_sector

MatchCandidate = namedtuple("MatchCandidate", [
    "signal_id", "company_id", "match_type", "match_score", "match_reason",
])

ACTIONABLE_SIGNAL_TYPES = {"regulatory", "ma", "leadership", "gov_contract", "earnings"}
MAX_LLM_BATCHES = 20
RELEVANCE_THRESHOLD = 0.4

STOPWORDS = {
    "inc", "inc.", "ltd", "ltd.", "plc", "corp", "corp.", "the", "and",
    "company", "corporation", "group", "holdings", "automotive",
    "technologies", "international", "energy",
}

SHORT_NAMES = {
    "Ford Motor Company": ["Ford"],
    "General Motors": ["GM"],
    "Tesla Inc": ["Tesla"],
    "Honda Motor Co": ["Honda"],
    "Rivian Automotive": ["Rivian"],
    "Lucid Group": ["Lucid"],
    "Stellantis NV": ["Stellantis"],
    "Aptiv": ["Aptiv"],
    "Magna International": ["Magna"],
    "Lockheed Martin": ["Lockheed"],
    "Boeing Company": ["Boeing"],
    "RTX Corporation": ["RTX", "Raytheon"],
    "Northrop Grumman": ["Northrop"],
    "General Dynamics": ["General Dynamics"],
    "L3Harris Technologies": ["L3Harris"],
    "Leidos Holdings": ["Leidos"],
    "ExxonMobil": ["Exxon", "ExxonMobil"],
    "Chevron Corporation": ["Chevron"],
    "Shell plc": ["Shell"],
    "ConocoPhillips": ["ConocoPhillips", "Conoco"],
    "NextEra Energy": ["NextEra"],
    "Duke Energy": ["Duke Energy"],
    "Dominion Energy": ["Dominion Energy"],
    "Southern Company": ["Southern Company"],
    "AES Corporation": ["AES"],
    "Enbridge Inc": ["Enbridge"],
}


def match_signals_to_companies(
    db: Session, signal_ids: list[str] | None = None,
) -> dict:
    companies = db.query(Company).all()
    if not companies:
        return {"name_matches": 0, "industry_matches": 0, "talking_points_generated": 0}

    if signal_ids:
        signals = db.query(Signal).filter(Signal.id.in_(signal_ids)).all()
    else:
        signals = db.query(Signal).all()

    if not signals:
        return {"name_matches": 0, "industry_matches": 0, "talking_points_generated": 0}

    existing = set(
        (r.signal_id, r.company_id)
        for r in db.query(SignalCompanyMatch.signal_id, SignalCompanyMatch.company_id).all()
    )

    signals_by_id = {s.id: s for s in signals}
    companies_by_id = {c.id: c for c in companies}

    # Stage 1: Name matching
    name_candidates = _name_match(signals, companies, existing)
    name_pairs = {(c.signal_id, c.company_id) for c in name_candidates}

    # Stage 2: Industry matching (skip pairs already name-matched)
    combined_existing = existing | name_pairs
    industry_candidates = _industry_match(signals, companies, combined_existing)

    # Stage 3: LLM relevance filter on industry candidates
    if industry_candidates and is_llm_available():
        semantic_candidates = _llm_relevance_filter(
            industry_candidates, signals_by_id, companies_by_id,
        )
    else:
        semantic_candidates = industry_candidates

    # Write all matches to DB
    all_new = []
    for c in name_candidates:
        match = SignalCompanyMatch(
            signal_id=c.signal_id,
            company_id=c.company_id,
            match_score=c.match_score,
            match_type=c.match_type,
            match_reason=c.match_reason,
        )
        db.add(match)
        all_new.append(match)

    for c in semantic_candidates:
        match = SignalCompanyMatch(
            signal_id=c.signal_id,
            company_id=c.company_id,
            match_score=c.match_score,
            match_type=c.match_type,
            match_reason=c.match_reason,
        )
        db.add(match)
        all_new.append(match)

    db.flush()

    # Stage 4: Talking points
    tp_count = _generate_talking_points(all_new, signals_by_id, companies_by_id, db)

    db.commit()

    return {
        "name_matches": len(name_candidates),
        "industry_matches": len(semantic_candidates),
        "talking_points_generated": tp_count,
    }


def _name_match(
    signals: list[Signal],
    companies: list[Company],
    existing_pairs: set[tuple[str, str]],
) -> list[MatchCandidate]:
    candidates = []
    for company in companies:
        search_terms = SHORT_NAMES.get(company.name, [])
        if not search_terms:
            name_parts = [
                p for p in company.name.split()
                if p.lower() not in STOPWORDS and len(p) > 2
            ]
            if name_parts:
                search_terms = [company.name] + (
                    [name_parts[0]] if len(name_parts[0]) > 3 else []
                )

        if not search_terms:
            continue

        for signal in signals:
            if (signal.id, company.id) in existing_pairs:
                continue

            text = f"{signal.title} {signal.body or ''}".lower()

            matched = False
            matched_term = ""
            for term in search_terms:
                if re.search(r'\b' + re.escape(term.lower()) + r'\b', text):
                    matched = True
                    matched_term = term
                    break

            if matched:
                candidates.append(MatchCandidate(
                    signal_id=signal.id,
                    company_id=company.id,
                    match_type="name",
                    match_score=1.0,
                    match_reason=f"'{matched_term}' found in signal text",
                ))
    return candidates


def _industry_match(
    signals: list[Signal],
    companies: list[Company],
    existing_pairs: set[tuple[str, str]],
) -> list[MatchCandidate]:
    candidates = []
    companies_by_industry: dict[str, list[Company]] = {}
    for c in companies:
        if c.industry:
            companies_by_industry.setdefault(c.industry, []).append(c)

    for signal in signals:
        if not signal.industry:
            continue
        if signal.signal_type not in ACTIONABLE_SIGNAL_TYPES:
            continue

        matched_companies = companies_by_industry.get(signal.industry, [])
        for company in matched_companies:
            if (signal.id, company.id) in existing_pairs:
                continue

            score = 0.4
            if signal.sub_sector and company.sub_sector and signal.sub_sector == company.sub_sector:
                score = 0.6

            candidates.append(MatchCandidate(
                signal_id=signal.id,
                company_id=company.id,
                match_type="industry",
                match_score=score,
                match_reason=f"Industry match: {signal.industry}"
                + (f" / {signal.sub_sector}" if signal.sub_sector == company.sub_sector else ""),
            ))

    return candidates


def _llm_relevance_filter(
    candidates: list[MatchCandidate],
    signals_by_id: dict[str, Signal],
    companies_by_id: dict[str, Company],
) -> list[MatchCandidate]:
    batch_size = 8
    batches = [candidates[i:i + batch_size] for i in range(0, len(candidates), batch_size)]
    batches = batches[:MAX_LLM_BATCHES]

    filtered = []
    for batch in batches:
        pairs_text = []
        for idx, c in enumerate(batch, 1):
            signal = signals_by_id[c.signal_id]
            company = companies_by_id[c.company_id]
            title = signal.title[:150]
            body_snippet = (signal.body or "")[:100]
            pairs_text.append(
                f'{idx}. Signal: "{title}" ({body_snippet}...) '
                f'| Company: "{company.name}" ({company.industry}/{company.sub_sector or "general"})'
            )

        prompt = (
            "You are evaluating whether market signals are relevant to specific companies.\n\n"
            "For each signal-company pair below, score relevance from 0.0 to 1.0:\n"
            "- 0.0-0.2: No meaningful connection\n"
            "- 0.3-0.5: Tangentially related (same broad industry)\n"
            "- 0.6-0.8: Likely relevant (affects company's specific market segment)\n"
            "- 0.9-1.0: Directly relevant (mentions company's products, competitors, or regulations)\n\n"
            "Pairs to evaluate:\n"
            + "\n".join(pairs_text) + "\n\n"
            "Return ONLY a JSON array, no other text:\n"
            '[{"pair": 1, "score": 0.7, "reason": "brief explanation"}, ...]'
        )

        result = call_llm(prompt, max_tokens=1000)
        scored = _parse_relevance_response(result, batch)

        for candidate, score, reason in scored:
            if score >= RELEVANCE_THRESHOLD:
                filtered.append(MatchCandidate(
                    signal_id=candidate.signal_id,
                    company_id=candidate.company_id,
                    match_type="semantic",
                    match_score=score,
                    match_reason=reason,
                ))

    remaining = candidates[MAX_LLM_BATCHES * batch_size:]
    filtered.extend(remaining)

    return filtered


def _parse_relevance_response(
    response: str,
    batch: list[MatchCandidate],
) -> list[tuple[MatchCandidate, float, str]]:
    if not response:
        return [(c, c.match_score, c.match_reason) for c in batch]

    try:
        start = response.find("[")
        end = response.rfind("]") + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
        else:
            return [(c, c.match_score, c.match_reason) for c in batch]
    except (json.JSONDecodeError, ValueError):
        return [(c, c.match_score, c.match_reason) for c in batch]

    results = []
    scores_by_pair = {item.get("pair"): item for item in data if isinstance(item, dict)}

    for idx, candidate in enumerate(batch, 1):
        item = scores_by_pair.get(idx)
        if item:
            score = min(1.0, max(0.0, float(item.get("score", candidate.match_score))))
            reason = item.get("reason", candidate.match_reason) or candidate.match_reason
            results.append((candidate, score, reason))
        else:
            results.append((candidate, candidate.match_score, candidate.match_reason))

    return results


def _generate_talking_points(
    matches: list[SignalCompanyMatch],
    signals_by_id: dict[str, Signal],
    companies_by_id: dict[str, Company],
    db: Session,
) -> int:
    if not matches:
        return 0

    if not is_llm_available():
        count = 0
        for match in matches:
            signal = signals_by_id.get(match.signal_id)
            company = companies_by_id.get(match.company_id)
            if signal and company:
                match.talking_points = _template_talking_points(signal, company)
                count += 1
        return count

    batch_size = 5
    count = 0

    for i in range(0, len(matches), batch_size):
        batch = matches[i:i + batch_size]
        match_descriptions = []

        industries_needed = set()
        for idx, match in enumerate(batch, 1):
            signal = signals_by_id.get(match.signal_id)
            company = companies_by_id.get(match.company_id)
            if not signal or not company:
                continue
            if company.industry:
                industries_needed.add(company.industry)
            match_descriptions.append(
                f'{idx}. Signal: "{signal.title[:200]}" ({signal.signal_type or "news"})\n'
                f'   Company: "{company.name}" ({company.client_status} client, '
                f'{company.industry or "unknown"}/{company.sub_sector or "general"})'
            )

        if not match_descriptions:
            continue

        capabilities_sections = []
        for industry in industries_needed:
            caps = get_capabilities_for_sector(industry)
            if caps:
                capabilities_sections.append(f"### {industry}\n{caps}")
        capabilities_text = "\n\n".join(capabilities_sections) if capabilities_sections else "No taxonomy loaded."

        prompt = (
            "You are a Strategy& consultant preparing talking points for partner meetings.\n\n"
            "For each signal-company match below, write 3-4 concise bullet points that:\n"
            "1. Explain why this signal matters to this specific company\n"
            "2. Connect it to a specific S& capability the company might need\n"
            "3. Suggest a conversation opener for a partner meeting\n\n"
            f"## S& Capabilities\n{capabilities_text}\n\n"
            "## Matches\n" + "\n".join(match_descriptions) + "\n\n"
            'Return ONLY a JSON object mapping match number to bullet array, no other text:\n'
            '{"1": ["bullet 1", "bullet 2", "bullet 3"], "2": [...]}'
        )

        result = call_llm(prompt, max_tokens=2000)
        parsed = _parse_talking_points_response(result, len(batch))

        for idx, match in enumerate(batch, 1):
            points = parsed.get(idx)
            if points:
                match.talking_points = "\n".join(f"- {p}" for p in points)
                count += 1
            else:
                signal = signals_by_id.get(match.signal_id)
                company = companies_by_id.get(match.company_id)
                if signal and company:
                    match.talking_points = _template_talking_points(signal, company)
                    count += 1

    return count


def _parse_talking_points_response(response: str, batch_len: int) -> dict[int, list[str]]:
    if not response:
        return {}

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
        else:
            return {}
    except (json.JSONDecodeError, ValueError):
        return {}

    result = {}
    for key, value in data.items():
        try:
            idx = int(key)
        except ValueError:
            continue
        if isinstance(value, list) and 1 <= idx <= batch_len:
            result[idx] = [str(v) for v in value if v]

    return result


def _template_talking_points(signal: Signal, company: Company) -> str:
    sig_type = (signal.signal_type or "news").replace("_", " ")
    industry = (company.industry or "their industry").replace("_", " ")
    sub_sector = (company.sub_sector or "operations").replace("_", " ")
    caps = get_capabilities_for_sector(company.industry)
    first_cap_group = caps.split("\n")[0] if caps else "Strategy & Operations"

    return (
        f"- This {sig_type} signal is relevant to {company.name}'s {sub_sector} business\n"
        f"- Consider how this may impact {company.name}'s strategic priorities in {industry}\n"
        f"- Review S& capabilities: {first_cap_group}\n"
        f"- Potential conversation starter: ask how {company.name} is responding to this development"
    )
