from datetime import datetime, timezone

import httpx

from app.collectors.base import BaseCollector, RawJob


class AshbyCollector(BaseCollector):
    source = "ashby"

    async def fetch_jobs(self, board_token: str) -> list[RawJob]:
        url = "https://api.ashbyhq.com/posting-api/job-board/{board}".format(board=board_token)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        jobs: list[RawJob] = []
        for item in data.get("jobs", []):
            is_remote = item.get("isRemote", False)
            jobs.append(
                RawJob(
                    external_id=item.get("id", ""),
                    title=item.get("title", ""),
                    description=item.get("descriptionHtml", ""),
                    department=item.get("department"),
                    remote_type="remote" if is_remote else "onsite",
                    apply_url=item.get("jobUrl"),
                    posted_at=datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00")) if item.get("publishedAt") else datetime.now(timezone.utc),
                    locations=[{"city": item.get("location"), "is_remote": is_remote}],
                )
            )
        return jobs
