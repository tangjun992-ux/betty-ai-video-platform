"""Small first-party product event collector (no third-party tracking)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import resolve_user_id
from app.metrics import ONBOARDING_EVENTS

router = APIRouter()

ALLOWED = {
    "started",
    "prompt_ready",
    "generation_submitted",
    "first_work_completed",
    "dismissed",
}


class OnboardingEvent(BaseModel):
    event: str


@router.post("/events/onboarding", summary="首作品激活漏斗事件")
async def onboarding_event(body: OnboardingEvent, user_id: int = Depends(resolve_user_id)):
    event = body.event if body.event in ALLOWED else "unknown"
    ONBOARDING_EVENTS.labels(event=event).inc()
    return {"accepted": True, "event": event, "user_id": user_id}
