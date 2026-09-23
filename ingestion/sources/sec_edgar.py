from datetime import datetime, timezone

from ingestion.sources.base import BaseSource, RawSignal
from ingestion.sources.http_client import get as http_get

EDGAR_FULLTEXT_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_RSS_URL = "https://www.sec.gov/cgi-bin/browse-edgar"

# SIC codes for target industries
SIC_CODES = {
    "motor_vehicles": "3711",
    "motor_vehicle_parts": "3714",
    "aircraft": "3721",
    "guided_missiles": "3760",
    "search_detection": "3812",
}


class SECEdgarSource(BaseSource):
    """Fetches recent SEC filings via EDGAR company search. Free, no key required."""

    def fetch(self, keywords: list[str], max_results: int = 20) -> list[RawSignal]:
        headers = {"User-Agent": "SalesIntelligencePlatform/0.1 (ai-pod-project)"}
        signals = []

        for industry_label, sic in SIC_CODES.items():
            if len(signals) >= max_results:
                break

            params = {
                "action": "getcompany",
                "type": "8-K",
                "dateb": "",
                "owner": "include",
                "count": "10",
                "search_text": "",
                "SIC": sic,
                "output": "atom",
            }

            try:
                resp = http_get(EDGAR_RSS_URL, params=params, headers=headers)
                resp.raise_for_status()
            except Exception as e:
                print(f"  SEC EDGAR fetch failed for SIC {sic}: {e}")
                continue

            signals.extend(self._parse_atom_feed(resp.text, industry_label))

        return signals[:max_results]

    def _parse_atom_feed(self, xml_text: str, industry_label: str) -> list[RawSignal]:
        import xml.etree.ElementTree as ET

        signals = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            link_el = entry.find("atom:link", ns)
            updated_el = entry.find("atom:updated", ns)
            summary_el = entry.find("atom:summary", ns)

            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            if not title:
                continue

            url = link_el.get("href") if link_el is not None else None
            published = None
            if updated_el is not None and updated_el.text:
                try:
                    published = datetime.fromisoformat(updated_el.text.replace("Z", "+00:00"))
                except ValueError:
                    pass

            body = summary_el.text.strip() if summary_el is not None and summary_el.text else None

            signals.append(RawSignal(
                title=title,
                body=body,
                url=url,
                source_name="sec_edgar",
                published_at=published,
            ))

        return signals
