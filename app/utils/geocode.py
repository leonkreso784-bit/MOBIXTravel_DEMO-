import os
from typing import Optional, Dict

import httpx


async def reverse_geocode(lat: float, lng: float, language_code: str = "en", google_key: Optional[str] = None) -> Dict[str, Optional[str]]:
    key = (google_key or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not key:
        return {"label": "My location", "city": None, "country": None}
    params = {
        "latlng": f"{lat},{lng}",
        "key": key,
        "language": language_code or "en",
        "result_type": "locality|postal_code|political",
    }
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    results = data.get("results", [])
    if not results:
        return {"label": "My location", "city": None, "country": None}
    primary = results[0]
    components = primary.get("address_components", [])

    def find_component(component_type: str) -> Optional[str]:
        for component in components:
            if component_type in component.get("types", []):
                return component.get("long_name")
        return None

    city = find_component("locality") or find_component("postal_town")
    country = find_component("country")
    label = primary.get("formatted_address") or city or "My location"
    return {"label": label, "city": city, "country": country}
