import os
from typing import List, Dict, Optional
from urllib.parse import quote_plus

import httpx

CATEGORY_CONFIG = {
    "restaurants": {
        "keywords": ["restaurant", "restoran", "eat", "dining", "food", "bistro"],
        "query": "best restaurants",
        "label": "restaurants",
        "card_type": "restaurant",
    },
    "nightlife": {
        "keywords": ["club", "nightclub", "bar", "nightlife", "party", "noćni", "nocni", "klub", "zabava", "izlazak", "clubbing"],
        "query": "best nightlife",
        "label": "nightlife spots",
        "card_type": "activity",
    },
    "cafes": {
        "keywords": ["cafe", "coffee", "kafić", "kafic", "espresso"],
        "query": "cozy cafes",
        "label": "cafés",
        "card_type": "restaurant",
    },
    "hotels": {
        "keywords": ["hotel", "stay", "accommodation", "smještaj"],
        "query": "top hotels",
        "label": "hotels",
        "card_type": "hotel",
    },
    "activities": {
        "keywords": ["things to do", "što raditi", "activities", "attractions", "poi", "zanimljivosti", "sights"],
        "query": "things to do",
        "label": "activities",
        "card_type": "activity",
    },
}

DEFAULT_CATEGORY = "activities"

FALLBACK_TEMPLATES = {
    "restaurants": [
        {"name": "Atelier {city}", "address": "Historic center, {city}", "rating": 4.8},
        {"name": "Sea Salt Kitchen", "address": "Waterfront promenade, {city}", "rating": 4.6},
        {"name": "Urban Garden", "address": "Design district, {city}", "rating": 4.7},
    ],
    "nightlife": [
        {"name": "Club Aurora", "address": "Old town arches, {city}", "rating": 4.5},
        {"name": "Skyline Bar", "address": "Rooftop, {city} center", "rating": 4.6},
        {"name": "Basement Beats", "address": "Creative quarter, {city}", "rating": 4.4},
    ],
    "cafes": [
        {"name": "Kavana Botanika", "address": "City park edge, {city}", "rating": 4.7},
        {"name": "Espresso Society", "address": "Main square, {city}", "rating": 4.6},
        {"name": "Velvet Roast", "address": "Art district, {city}", "rating": 4.5},
    ],
    "hotels": [
        {"name": "Grand Palace {city}", "address": "Central boulevard", "rating": 4.8},
        {"name": "Boutique Atelier", "address": "Old town courtyard", "rating": 4.6},
        {"name": "Harborline Suites", "address": "Seafront", "rating": 4.7},
    ],
    "activities": [
        {"name": "Panoramic Walk", "address": "Riverside trail, {city}", "rating": 4.9},
        {"name": "Local Market Tour", "address": "Green market, {city}", "rating": 4.7},
        {"name": "Contemporary Art Hub", "address": "Museumska zona, {city}", "rating": 4.6},
    ],
}

GOOGLE_API_KEY = (os.getenv("GOOGLE_API_KEY") or "").strip()


def detect_category(message: str) -> str:
    msg = (message or "").lower()
    for category, config in CATEGORY_CONFIG.items():
        if any(keyword in msg for keyword in config["keywords"]):
            return category
    return DEFAULT_CATEGORY


def get_category_query(category: str) -> str:
    return CATEGORY_CONFIG.get(category, CATEGORY_CONFIG[DEFAULT_CATEGORY])["query"]


def get_category_label(category: str) -> str:
    return CATEGORY_CONFIG.get(category, CATEGORY_CONFIG[DEFAULT_CATEGORY])["label"]


def get_category_card_type(category: str) -> str:
    return CATEGORY_CONFIG.get(category, CATEGORY_CONFIG[DEFAULT_CATEGORY])["card_type"]


async def search_places(
    query: str,
    city: Optional[str],
    limit: int = 6,
    language_code: str = "en",
    google_key: Optional[str] = None,
) -> List[Dict[str, any]]:
    """Search for places using Google Places API or return fallback data."""
    key = (google_key or GOOGLE_API_KEY or "").strip()
    category = _infer_category_from_query(query)
    
    if not key:
        return _fallback_places(category, city, limit)
        
    effective_query = query if city is None else f"{query} in {city}"
    params = {
        "query": effective_query,
        "key": key,
        "language": language_code or "en",
    }
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Check if API returned error status
            if data.get("status") != "OK":
                return _fallback_places(category, city, limit)
                
    except (httpx.HTTPError, Exception):
        return _fallback_places(category, city, limit)
        
    results = []
    for result in data.get("results", [])[:limit]:
        place_id = result.get("place_id")
        place_name = result.get("name", "")
        if not place_name:  # Skip invalid results
            continue
            
        maps_url = (
            f"https://www.google.com/maps/place/?q=place_id:{place_id}"
            if place_id
            else f"https://www.google.com/maps/search/?api=1&query={quote_plus(place_name)}"
        )
        geometry = result.get("geometry", {}).get("location", {})
        
        # Get photo reference if available
        photos = result.get("photos", [])
        
        results.append(
            {
                "name": place_name,
                "rating": result.get("rating"),
                "user_ratings_total": result.get("user_ratings_total"),
                "address": result.get("formatted_address", ""),
                "price_level": result.get("price_level"),
                "types": result.get("types", []),
                "maps_url": maps_url,
                "lat": geometry.get("lat"),
                "lng": geometry.get("lng"),
                "photos": photos,  # Include photo references
                "place_id": place_id,
            }
        )
    
    # Always return fallback if no valid results
    if not results:
        return _fallback_places(category, city, limit)
    return results


def _infer_category_from_query(query: str) -> str:
    text = (query or "").lower()
    for category, config in CATEGORY_CONFIG.items():
        if any(keyword in text for keyword in config["keywords"]):
            return category
    return DEFAULT_CATEGORY


def _fallback_places(category: str, city: Optional[str], limit: int) -> List[Dict[str, str]]:
    city_name = city or "Zagreb"
    template_list = FALLBACK_TEMPLATES.get(category) or FALLBACK_TEMPLATES[DEFAULT_CATEGORY]
    results: List[Dict[str, str]] = []
    for template in template_list[:limit]:
        name = template["name"].format(city=city_name.title())
        address = template["address"].format(city=city_name.title())
        results.append(
            {
                "name": name,
                "rating": template.get("rating"),
                "address": address,
                "price_level": None,
                "types": [category],
                "maps_url": f"https://www.google.com/maps/search/?api=1&query={quote_plus(name + ' ' + city_name)}",
                "lat": None,
                "lng": None,
                "city": city_name.title(),
            }
        )
    return results
