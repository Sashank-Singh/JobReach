from app.collectors.ashby import AshbyCollector
from app.collectors.base import BaseCollector
from app.collectors.greenhouse import GreenhouseCollector
from app.collectors.lever import LeverCollector

COLLECTORS: dict[str, BaseCollector] = {
    "greenhouse": GreenhouseCollector(),
    "lever": LeverCollector(),
    "ashby": AshbyCollector(),
}


def get_collector(ats_type: str) -> BaseCollector | None:
    return COLLECTORS.get(ats_type)
