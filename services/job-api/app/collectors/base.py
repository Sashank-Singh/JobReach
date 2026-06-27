from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawJob:
    external_id: str
    title: str
    description: str | None = None
    department: str | None = None
    experience_level: str | None = None
    remote_type: str | None = None
    visa_sponsorship: bool | None = None
    apply_url: str | None = None
    posted_at: datetime | None = None
    locations: list[dict] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    salary: dict | None = None


class BaseCollector(ABC):
    source: str

    @abstractmethod
    async def fetch_jobs(self, board_token: str) -> list[RawJob]:
        pass
