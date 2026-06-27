from datetime import datetime, timezone

import httpx

from app.collectors.base import BaseCollector, RawJob
from app.utils.experience import infer_experience_level
from app.utils.location import parse_location
from app.utils.remote import infer_remote_type


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
            loc = item.get("location") or ""
            is_remote = item.get("isRemote", False)
            parsed = parse_location(loc)
            remote_type = "remote" if is_remote else infer_remote_type(loc, item.get("title", ""))
            jobs.append(
                RawJob(
                    external_id=item.get("id", ""),
                    title=item.get("title", ""),
                    description=item.get("descriptionHtml", ""),
                    department=item.get("department"),
                    experience_level=infer_experience_level(item.get("title", "")),
                    remote_type=remote_type,
                    apply_url=item.get("jobUrl"),
                    posted_at=datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00")) if item.get("publishedAt") else datetime.now(timezone.utc),
                    locations=[{
                        "city": parsed["display"] or loc,
                        "state": parsed["state"],
                        "country": parsed["country"],
                        "is_remote": is_remote or parsed["is_remote"],
                    }] if loc else [],
                )
            )
        return jobs
