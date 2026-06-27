from datetime import datetime, timezone

import httpx

from app.collectors.base import BaseCollector, RawJob


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
            locations = [{"city": loc.get("name"), "is_remote": "remote" in (loc.get("name") or "").lower()} for loc in item.get("location", {}).get("name", [])] if isinstance(item.get("location"), dict) else [{"city": item.get("location", {}).get("name") if item.get("location") else None}]

            loc_name = item.get("location", {}).get("name") if isinstance(item.get("location"), dict) else str(item.get("location", ""))
            remote_type = "remote" if loc_name and "remote" in loc_name.lower() else "onsite"

            jobs.append(
                RawJob(
                    external_id=str(item["id"]),
                    title=item.get("title", ""),
                    description=item.get("content", ""),
                    department=item.get("departments", [{}])[0].get("name") if item.get("departments") else None,
                    remote_type=remote_type,
                    apply_url=item.get("absolute_url"),
                    posted_at=datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")) if item.get("updated_at") else datetime.now(timezone.utc),
                    locations=[{"city": loc_name, "is_remote": remote_type == "remote"}] if loc_name else [],
                )
            )
        return jobs
