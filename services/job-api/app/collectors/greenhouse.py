from datetime import datetime, timezone

import httpx

from app.collectors.base import BaseCollector, RawJob
from app.utils.experience import infer_experience_level
from app.utils.location import parse_location
from app.utils.remote import infer_remote_type


class GreenhouseCollector(BaseCollector):
    source = "greenhouse"

    async def fetch_jobs(self, board_token: str) -> list[RawJob]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        jobs: list[RawJob] = []
        for item in data.get("jobs", []):
            loc_name = self._location_name(item.get("location"))
            parsed = parse_location(loc_name)
            remote_type = infer_remote_type(loc_name, item.get("title", "")) if loc_name else "onsite"
            if parsed["is_remote"]:
                remote_type = "remote"

            jobs.append(
                RawJob(
                    external_id=str(item["id"]),
                    title=item.get("title", ""),
                    description=item.get("content", ""),
                    department=item.get("departments", [{}])[0].get("name") if item.get("departments") else None,
                    experience_level=infer_experience_level(item.get("title", "")),
                    remote_type=remote_type,
                    apply_url=item.get("absolute_url"),
                    posted_at=datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
                    if item.get("updated_at")
                    else datetime.now(timezone.utc),
                    locations=[{
                        "city": parsed["display"] or loc_name,
                        "state": parsed["state"],
                        "country": parsed["country"],
                        "is_remote": parsed["is_remote"] or remote_type == "remote",
                    }] if loc_name else [],
                )
            )
        return jobs

    @staticmethod
    def _location_name(location: dict | str | None) -> str | None:
        if not location:
            return None
        if isinstance(location, dict):
            return location.get("name")
        return str(location)
