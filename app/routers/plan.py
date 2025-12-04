import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..utils.travel_bundle import build_travel_bundle, cards_from_bundle
from ..utils.formatters import format_travel_plan

router = APIRouter(prefix="/api", tags=["plan"])


class PlanPayload(BaseModel):
    origin: str
    destination: str
    budget: int | None = None
    session_id: str | None = None
    language_code: str | None = "en"


@router.post("/plan")
async def plan_trip(payload: PlanPayload):
    if not payload.origin or not payload.destination:
        raise HTTPException(status_code=400, detail="origin and destination required")
    language_code = (payload.language_code or "en").split("-")[0].lower()
    google_key = (os.getenv("GOOGLE_API_KEY") or "").strip()
    bundle = await build_travel_bundle(
        payload.origin,
        payload.destination,
        {"google": google_key},
        payload.budget,
        language_code,
    )
    plan_text = format_travel_plan(bundle, language_code)
    cards = cards_from_bundle(bundle)
    return {"plan": plan_text, "cards": cards, "bundle": bundle}
