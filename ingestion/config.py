import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DB_PATH = PROJECT_ROOT / "data" / "signals.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

AUTOMOTIVE_KEYWORDS = [
    "automotive", "electric vehicle", "EV", "OEM", "powertrain",
    "autonomous driving", "ADAS", "battery", "charging infrastructure",
    "General Motors", "GM", "Ford", "Stellantis", "Toyota", "Honda",
    "Volkswagen", "BMW", "Mercedes", "Tesla", "Rivian", "Lucid",
    "BYD", "Hyundai", "Kia", "Nissan", "NHTSA", "emissions",
    "fuel economy", "CAFE standards", "vehicle safety", "recall",
    "auto parts", "tier 1 supplier", "ZF", "Bosch", "Continental",
    "Magna", "Aptiv", "Denso", "car sales", "vehicle production",
    "auto supplier", "automaker", "car manufacturer", "vehicle",
    "auto industry", "auto-parts", "automobile",
]

AEROSPACE_DEFENSE_KEYWORDS = [
    "aerospace", "defense", "defence", "military", "Pentagon",
    "Lockheed Martin", "Boeing", "Raytheon", "RTX", "Northrop Grumman",
    "General Dynamics", "BAE Systems", "L3Harris", "Leidos",
    "ITAR", "EAR", "export control", "DoD", "Department of Defense",
    "DARPA", "Air Force", "Navy", "Army", "Space Force",
    "F-35", "hypersonic", "missile defense", "satellite",
    "unmanned", "drone", "UAV", "defense budget", "NDAA",
    "defense contract", "FAA", "aviation", "aircraft",
    "space launch", "NASA", "munitions", "cybersecurity defense",
]

ENERGY_KEYWORDS = [
    "energy transition", "renewable energy", "solar", "wind power",
    "natural gas", "LNG", "oil and gas", "upstream", "downstream",
    "midstream", "refinery", "pipeline", "FERC", "NERC",
    "grid modernization", "power grid", "utilities", "energy storage",
    "hydrogen", "carbon capture", "CCS", "CCUS", "nuclear energy",
    "ExxonMobil", "Chevron", "Shell", "BP", "ConocoPhillips",
    "TotalEnergies", "NextEra Energy", "Duke Energy", "Dominion Energy",
    "Southern Company", "AES", "Enbridge", "Kinder Morgan",
    "clean energy", "energy policy", "IRA", "Inflation Reduction Act",
    "DOE", "Department of Energy", "OPEC", "energy security",
    "power purchase agreement", "PPA", "decarbonization",
    "methane", "emissions reduction", "energy infrastructure",
    "offshore wind", "onshore wind", "battery storage", "EV charging",
    "smart grid", "distributed energy", "microgrids",
]

ALL_KEYWORDS = AUTOMOTIVE_KEYWORDS + AEROSPACE_DEFENSE_KEYWORDS + ENERGY_KEYWORDS
