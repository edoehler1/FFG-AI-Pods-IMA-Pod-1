from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawSignal:
    title: str
    body: str | None
    url: str | None
    source_name: str
    published_at: datetime | None


class BaseSource(ABC):
    @abstractmethod
    def fetch(self, keywords: list[str], max_results: int = 50) -> list[RawSignal]:
        pass
