from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..utils.categories import search_places
from ..utils.formatters import format_specific_search_response

router = APIRouter(prefix="/api", tags=["places"])


class PlacesPayload(BaseModel):
    query: str
    city: str | None = None
    language_code: str = "en"


@router.post("/places")
async def places_search(payload: PlacesPayload):
    if not payload.query:
        raise HTTPException(status_code=400, detail="query required")
    places = await search_places(payload.query, payload.city, language_code=payload.language_code)
    if not places:
        raise HTTPException(status_code=404, detail="No results")
    reply = format_specific_search_response(payload.query, payload.city or "city", places)
    return {"results": places, "reply": reply}
