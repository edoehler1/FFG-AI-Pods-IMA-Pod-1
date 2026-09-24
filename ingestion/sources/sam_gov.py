import os
from datetime import datetime, timedelta, timezone

from ingestion.sources.base import BaseSource, RawSignal
from ingestion.sources.http_client import get as http_get

SAM_API_URL = "https://api.sam.gov/opportunities/v2/search"


class SAMGovSource(BaseSource):
    """Fetches government contract opportunities from the SAM.gov API. Requires SAM_GOV_API_KEY."""

    def fetch(self, keywords: list[str], max_results: int = 50) -> list[RawSignal]:
        api_key = os.environ.get("SAM_GOV_API_KEY", "")
        if not api_key:
            print("  SAM.gov API key not configured — skipping (set SAM_GOV_API_KEY in .env)")
            return []

        today = datetime.now(timezone.utc)
        ninety_days_ago = today - timedelta(days=90)

        params = {
            "api_key": api_key,
            "keyword": ",".join(keywords[:6]),
            "postedFrom": ninety_days_ago.strftime("%m/%d/%Y"),
            "postedTo": today.strftime("%m/%d/%Y"),
            "limit": str(max_results),
            "offset": "0",
        }

        try:
            resp = http_get(SAM_API_URL, params=params)
            resp.raise_for_status()
        except Exception as e:
            print(f"  SAM.gov fetch failed: {e}")
            return []

        data = resp.json()
        opportunities = data.get("opportunitiesData", [])

        signals = []
        for opp in opportunities:
            title = opp.get("title", "").strip()
            if not title:
                continue

            description = opp.get("description", "")
            naics = opp.get("naicsCode", "N/A")
            set_aside = opp.get("typeOfSetAside", "None")
            deadline = opp.get("responseDeadLine", "N/A")
            body = f"{description} | NAICS: {naics} | Set-aside: {set_aside} | Response deadline: {deadline}"[:1000]

            notice_id = opp.get("noticeId", "")
            url = f"https://sam.gov/opp/{notice_id}/view" if notice_id else None

            published = self._parse_date(opp.get("postedDate"))

            signals.append(RawSignal(
                title=title,
                body=body,
                url=url,
                source_name="sam_gov",
                published_at=published,
            ))

        return signals

    @staticmethod
    def _parse_date(date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None
