from datetime import datetime, timedelta, timezone

from ingestion.sources.base import BaseSource, RawSignal
from ingestion.sources.http_client import post as http_post

USASPENDING_API_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"


class USASpendingSource(BaseSource):
    """Fetches federal contract award data from USASpending.gov. Free, no key required."""

    def fetch(self, keywords: list[str], max_results: int = 50) -> list[RawSignal]:
        today = datetime.now(timezone.utc)
        ninety_days_ago = today - timedelta(days=90)

        payload = {
            "filters": {
                "keywords": keywords[:10],
                "time_period": [
                    {
                        "start_date": ninety_days_ago.strftime("%Y-%m-%d"),
                        "end_date": today.strftime("%Y-%m-%d"),
                    }
                ],
                "award_type_codes": ["A", "B", "C", "D"],
            },
            "fields": [
                "Award ID",
                "Description",
                "Start Date",
                "End Date",
                "Award Amount",
                "Awarding Agency",
                "Recipient Name",
            ],
            "limit": max_results,
            "page": 1,
            "sort": "Start Date",
            "order": "desc",
        }

        try:
            resp = http_post(USASPENDING_API_URL, json=payload)
            resp.raise_for_status()
        except Exception as e:
            print(f"  USASpending fetch failed: {e}")
            return []

        data = resp.json()
        results = data.get("results", [])

        signals = []
        for award in results:
            recipient = award.get("Recipient Name", "")
            amount = award.get("Award Amount", 0) or 0
            award_id = award.get("Award ID", "")

            if recipient:
                title = f"{recipient} — ${amount:,.0f} contract"
            else:
                title = f"Federal Award {award_id}" if award_id else "Federal Contract Award"

            description = award.get("Description", "")
            agency = award.get("Awarding Agency", "N/A")
            body = f"{description} | Agency: {agency} | Amount: ${amount:,.0f}"[:1000]

            url = f"https://www.usaspending.gov/award/{award_id}" if award_id else None

            published = None
            if start_date := award.get("Start Date"):
                try:
                    published = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            signals.append(RawSignal(
                title=title,
                body=body,
                url=url,
                source_name="usaspending",
                published_at=published,
            ))

        return signals
