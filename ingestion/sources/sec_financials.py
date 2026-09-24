"""
Fetches structured financial data from the SEC XBRL Company Facts API.
Returns actual numbers (revenue, net income, SG&A, etc.) not just filing metadata.
"""

from ingestion.sources.http_client import get as http_get
from ingestion.sources.sec_edgar import TARGET_COMPANIES

COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
HEADERS = {"User-Agent": "SalesIntelligencePlatform/0.1 (ai-pod-project@pwc.com)"}

KEY_METRICS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "NetIncomeLoss",
    "OperatingIncomeLoss",
    "GrossProfit",
    "SellingGeneralAndAdministrativeExpense",
    "Assets",
    "AssetsCurrent",
    "StockholdersEquity",
    "LongTermDebt",
    "CostOfRevenue",
    "CostOfGoodsSold",
    "OperatingExpenses",
    "ResearchAndDevelopmentExpense",
    "CapitalExpendituresIncurredButNotYetPaid",
    "PaymentsToAcquirePropertyPlantAndEquipment",
]

METRIC_LABELS = {
    "Revenues": "Revenue",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "Revenue",
    "NetIncomeLoss": "Net Income",
    "OperatingIncomeLoss": "Operating Income",
    "GrossProfit": "Gross Profit",
    "SellingGeneralAndAdministrativeExpense": "SG&A",
    "Assets": "Total Assets",
    "AssetsCurrent": "Current Assets",
    "StockholdersEquity": "Stockholders Equity",
    "LongTermDebt": "Long-Term Debt",
    "CostOfRevenue": "Cost of Revenue",
    "CostOfGoodsSold": "COGS",
    "OperatingExpenses": "Operating Expenses",
    "ResearchAndDevelopmentExpense": "R&D Expense",
    "CapitalExpendituresIncurredButNotYetPaid": "CapEx",
    "PaymentsToAcquirePropertyPlantAndEquipment": "CapEx (PP&E)",
}


def fetch_company_financials(cik: str, company_name: str) -> dict | None:
    try:
        resp = http_get(COMPANY_FACTS_URL.format(cik=cik), headers=HEADERS)
        resp.raise_for_status()
    except Exception as e:
        print(f"  Financial data failed for {company_name}: {e}")
        return None

    data = resp.json()
    gaap = data.get("facts", {}).get("us-gaap", {})
    if not gaap:
        return None

    financials = {}
    seen_labels = set()

    for metric_key in KEY_METRICS:
        if metric_key not in gaap:
            continue

        label = METRIC_LABELS.get(metric_key, metric_key)
        if label in seen_labels:
            continue

        entries = gaap[metric_key].get("units", {}).get("USD", [])
        quarterly = [
            e for e in entries
            if e.get("form") in ("10-K", "10-Q")
            and e.get("fp") in ("FY", "Q1", "Q2", "Q3", "Q4")
        ]
        quarterly.sort(key=lambda x: x.get("end", ""), reverse=True)

        if not quarterly:
            continue

        periods = []
        for e in quarterly[:8]:
            periods.append({
                "period": e.get("fp"),
                "end_date": e.get("end"),
                "value": e.get("val"),
                "form": e.get("form"),
            })

        financials[label] = periods
        seen_labels.add(label)

    return financials


def fetch_all_financials() -> dict[str, dict]:
    results = {}
    for cik, name in TARGET_COMPANIES.items():
        print(f"  Fetching financials for {name}...")
        data = fetch_company_financials(cik, name)
        if data:
            results[name] = data
    return results


def format_financials_for_prompt(financials: dict) -> str:
    if not financials:
        return "No structured financial data available."

    lines = []
    for metric, periods in financials.items():
        if not periods:
            continue

        values = []
        for p in periods[:4]:
            val = p["value"]
            if abs(val) >= 1e9:
                formatted = f"${val / 1e9:,.1f}B"
            elif abs(val) >= 1e6:
                formatted = f"${val / 1e6:,.0f}M"
            else:
                formatted = f"${val:,.0f}"
            values.append(f"{p['period']} {p['end_date'][:4]}: {formatted}")

        lines.append(f"**{metric}:** {' → '.join(values)}")

    return "\n".join(lines)
