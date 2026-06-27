from datetime import datetime, timezone

import httpx

from app.collectors.base import BaseCollector, RawJob
from app.utils.experience import infer_experience_level


class LeverCollector(BaseCollector):
    source = "lever"

    async def fetch_jobs(self, board_token: str) -> list[RawJob]:
        url = f"https://api.lever.co/v0/postings/{board_token}?mode=json"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        jobs: list[RawJob] = []
        for item in data:
            workplace = (item.get("workplaceType") or "").lower()
            remote_type = "remote" if workplace == "remote" else "hybrid" if workplace == "hybrid" else "onsite"

            jobs.append(
                RawJob(
                    external_id=item.get("id", ""),
                    title=item.get("text", ""),
                    description=item.get("descriptionPlain", ""),
                    department=item.get("categories", {}).get("team"),
                    experience_level=item.get("categories", {}).get("commitment") or infer_experience_level(item.get("text", "")),
                    remote_type=remote_type,
                    apply_url=item.get("hostedUrl"),
                    posted_at=datetime.fromtimestamp(item["createdAt"] / 1000, tz=timezone.utc) if item.get("createdAt") else None,
                    locations=[{"city": item.get("categories", {}).get("location"), "is_remote": remote_type == "remote"}],
                )
            )
        return jobs
