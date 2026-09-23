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

ALL_KEYWORDS = AUTOMOTIVE_KEYWORDS + AEROSPACE_DEFENSE_KEYWORDS
