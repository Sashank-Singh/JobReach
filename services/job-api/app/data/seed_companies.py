from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Company, Job

# Public ATS board tokens (Greenhouse / Lever / Ashby)
SEED_COMPANIES = [
    {"name": "Stripe", "slug": "stripe", "ats_type": "greenhouse", "ats_board_token": "stripe", "website": "https://stripe.com", "visa_sponsorship": True},
    {"name": "Figma", "slug": "figma", "ats_type": "greenhouse", "ats_board_token": "figma", "website": "https://figma.com", "visa_sponsorship": True},
    {"name": "Airbnb", "slug": "airbnb", "ats_type": "greenhouse", "ats_board_token": "airbnb", "website": "https://airbnb.com", "visa_sponsorship": True},
    {"name": "Coinbase", "slug": "coinbase", "ats_type": "greenhouse", "ats_board_token": "coinbase", "website": "https://coinbase.com", "visa_sponsorship": True},
    {"name": "Discord", "slug": "discord", "ats_type": "greenhouse", "ats_board_token": "discord", "website": "https://discord.com", "visa_sponsorship": True},
    {"name": "Databricks", "slug": "databricks", "ats_type": "greenhouse", "ats_board_token": "databricks", "website": "https://databricks.com", "visa_sponsorship": True},
    {"name": "Cloudflare", "slug": "cloudflare", "ats_type": "greenhouse", "ats_board_token": "cloudflare", "website": "https://cloudflare.com", "visa_sponsorship": True},
    {"name": "Datadog", "slug": "datadog", "ats_type": "greenhouse", "ats_board_token": "datadog", "website": "https://datadoghq.com", "visa_sponsorship": True},
    {"name": "DoorDash", "slug": "doordash", "ats_type": "greenhouse", "ats_board_token": "doordash", "website": "https://doordash.com", "visa_sponsorship": True},
    {"name": "Robinhood", "slug": "robinhood", "ats_type": "greenhouse", "ats_board_token": "robinhood", "website": "https://robinhood.com", "visa_sponsorship": True},
    {"name": "Notion", "slug": "notion", "ats_type": "ashby", "ats_board_token": "notion", "website": "https://notion.so", "visa_sponsorship": True},
    {"name": "Linear", "slug": "linear", "ats_type": "ashby", "ats_board_token": "linear", "website": "https://linear.app", "visa_sponsorship": True},
    {"name": "OpenAI", "slug": "openai", "ats_type": "ashby", "ats_board_token": "openai", "website": "https://openai.com", "visa_sponsorship": True},
    {"name": "Ramp", "slug": "ramp", "ats_type": "ashby", "ats_board_token": "ramp", "website": "https://ramp.com", "visa_sponsorship": True},
    {"name": "Anthropic", "slug": "anthropic", "ats_type": "ashby", "ats_board_token": "anthropic", "website": "https://anthropic.com", "visa_sponsorship": True},
    {"name": "Vercel", "slug": "vercel", "ats_type": "ashby", "ats_board_token": "vercel", "website": "https://vercel.com", "visa_sponsorship": True},
    {"name": "Retool", "slug": "retool", "ats_type": "ashby", "ats_board_token": "retool", "website": "https://retool.com", "visa_sponsorship": True},
    {"name": "Netflix", "slug": "netflix", "ats_type": "lever", "ats_board_token": "netflix", "website": "https://netflix.com", "visa_sponsorship": False},
    {"name": "Palantir", "slug": "palantir", "ats_type": "lever", "ats_board_token": "palantir", "website": "https://palantir.com", "visa_sponsorship": True},
    {"name": "Spotify", "slug": "spotify", "ats_type": "lever", "ats_board_token": "spotify", "website": "https://spotify.com", "visa_sponsorship": True},
    {"name": "Plaid", "slug": "plaid", "ats_type": "lever", "ats_board_token": "plaid", "website": "https://plaid.com", "visa_sponsorship": True},
    {"name": "Scale AI", "slug": "scaleai", "ats_type": "greenhouse", "ats_board_token": "scaleai", "website": "https://scale.com", "visa_sponsorship": True},
    {"name": "Anduril", "slug": "anduril", "ats_type": "greenhouse", "ats_board_token": "anduril", "website": "https://anduril.com", "visa_sponsorship": False},
    {"name": "Rippling", "slug": "rippling", "ats_type": "greenhouse", "ats_board_token": "rippling", "website": "https://rippling.com", "visa_sponsorship": True},
]


def enrich_company_stats(session: Session, company: Company) -> None:
    """Compute hiring velocity and interview difficulty from job data."""
    active_count = session.execute(
        select(func.count()).select_from(Job).where(Job.company_id == company.id, Job.is_active.is_(True))
    ).scalar() or 0

    company.hiring_velocity = active_count
    if company.interview_difficulty is None:
        company.interview_difficulty = min(5.0, 2.0 + active_count / 50)
    if company.employee_count is None:
        company.employee_count = max(500, active_count * 20)
