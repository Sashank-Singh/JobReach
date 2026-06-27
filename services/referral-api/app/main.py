from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.referrals import router as referrals_router
from app.core.config import settings

app = FastAPI(
    title="JobReach Referral Service",
    description="Developer 2 referral discovery, outreach, and CRM API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(referrals_router)
