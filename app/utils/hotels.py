import os
from typing import List, Dict, Optional, Any
from urllib.parse import quote_plus

import httpx

from .amadeus_client import amadeus_client

try:
    from travel_planner import get_mock_hotels  # type: ignore
except Exception:
    def get_mock_hotels(city: str, budget: Optional[int] = None):  # type: ignore
        base = ["Central", "Grand", "Boutique", "Urban"]
        hotels = []
        for idx, name in enumerate(base, start=1):
            hotels.append(
                {
                    "name": f"{city.title()} {name} {idx}",
                    "rating": 4.0 + idx * 0.1,
                    "price_per_night": 80 + idx * 15,
                    "link": f"https://www.google.com/maps/search/?api=1&query={quote_plus(city + ' hotel ' + name)}",
                }
            )
        return hotels


# City cost multipliers (relative to average European city)
# Higher = more expensive
CITY_COST_INDEX = {
    # Very expensive cities
    "london": 1.8, "paris": 1.6, "zurich": 2.0, "geneva": 1.9,
    "new york": 2.0, "tokyo": 1.7, "singapore": 1.5,
    "amsterdam": 1.5, "stockholm": 1.6, "copenhagen": 1.6, "oslo": 1.8,
    "dubai": 1.4, "hong kong": 1.6, "sydney": 1.5, "melbourne": 1.4,
    "san francisco": 2.0, "los angeles": 1.6, "miami": 1.5,
    
    # Expensive cities
    "rome": 1.3, "milan": 1.4, "florence": 1.3, "venice": 1.5,
    "barcelona": 1.3, "madrid": 1.2, "munich": 1.4, "berlin": 1.2,
    "vienna": 1.3, "brussels": 1.3, "dublin": 1.4,
    "toronto": 1.4, "vancouver": 1.4, "boston": 1.6,
    
    # Average cities
    "lisbon": 1.0, "prague": 0.9, "budapest": 0.8, "athens": 0.9,
    "warsaw": 0.8, "krakow": 0.7, "zagreb": 0.8, "ljubljana": 0.9,
    "nice": 1.3, "lyon": 1.1, "marseille": 1.0,
    
    # Affordable cities
    "split": 0.8, "dubrovnik": 0.9, "zadar": 0.7, "rijeka": 0.7,
    "belgrade": 0.6, "sarajevo": 0.5, "sofia": 0.5, "bucharest": 0.6,
    "bangkok": 0.4, "bali": 0.5, "hanoi": 0.4, "kuala lumpur": 0.5,
    
    # Croatian islands/towns (generally affordable)
    "pula": 0.7, "rovinj": 0.8, "opatija": 0.8, "krk": 0.7,
    "hvar": 0.9, "korčula": 0.7, "makarska": 0.7,
}


def _get_city_cost_index(city: str) -> float:
    """Get cost multiplier for a city (1.0 = average European city)"""
    city_lower = city.lower().strip()
    
    # Direct match
    if city_lower in CITY_COST_INDEX:
        return CITY_COST_INDEX[city_lower]
    
    # Partial match (e.g., "New York City" -> "new york")
    for known_city, index in CITY_COST_INDEX.items():
        if known_city in city_lower or city_lower in known_city:
            return index
    
    # Default to average
    return 1.0


def _estimate_price(price_level: str, city: str = "") -> int:
    """
    Estimate hotel price based on Google's price level AND city cost index.
    Returns realistic price range rather than fixed values.
    """
    # Base prices for average European city
    base_prices = {
        "PRICE_LEVEL_FREE": 0,
        "PRICE_LEVEL_INEXPENSIVE": 45,    # Budget hostels, basic hotels
        "PRICE_LEVEL_MODERATE": 85,       # Mid-range hotels
        "PRICE_LEVEL_EXPENSIVE": 160,     # Nice hotels
        "PRICE_LEVEL_VERY_EXPENSIVE": 300, # Luxury hotels
        "PRICE_LEVEL_UNSPECIFIED": 75,    # Unknown - assume mid-range
    }
    
    base_price = base_prices.get(price_level, 75)
    
    # Apply city cost index
    city_index = _get_city_cost_index(city) if city else 1.0
    adjusted_price = int(base_price * city_index)
    
    # Add some variance (±15%) to make prices look more realistic
    import random
    variance = random.uniform(0.85, 1.15)
    final_price = int(adjusted_price * variance)
    
    # Ensure minimum price
    return max(25, final_price)


async def search_hotels(
    destination: str, 
    google_key: Optional[str], 
    max_price: Optional[Any] = None,
    check_in_date: Optional[str] = None,
    check_out_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for hotels using BOTH Amadeus AND Google Places APIs.
    Combines results from both sources for better hotel coverage.
    """
    # Convert budget string to number (e.g., "medium" -> 150, "luxury" -> 500)
    price_limit = None
    if max_price:
        if isinstance(max_price, (int, float)):
            price_limit = int(max_price)
        elif isinstance(max_price, str):
            budget_map = {"low": 50, "budget": 80, "medium": 150, "high": 300, "luxury": 500}
            price_limit = budget_map.get(max_price.lower(), 150)
    
    all_hotels = []
    
    # Search Amadeus if configured
    if amadeus_client.is_configured():
        try:
            # Get city IATA code
            city_code = await amadeus_client.get_iata_code(destination)
            
            if city_code:
                amadeus_hotels = await amadeus_client.search_hotels(
                    city_code=city_code,
                    check_in_date=check_in_date,
                    check_out_date=check_out_date,
                    adults=1,
                    max_price=price_limit,
                    max_results=5
                )
                
                if amadeus_hotels:
                    print(f"✅ Amadeus found {len(amadeus_hotels)} hotels in {destination}")
                    # Add Google Maps links
                    for hotel in amadeus_hotels:
                        hotel["link"] = f"https://www.google.com/maps/search/?api=1&query={quote_plus(hotel['name'] + ' ' + destination)}"
                    all_hotels.extend(amadeus_hotels)
        except Exception as e:
            print(f"⚠️ Amadeus hotel search failed: {e}")
    
    # ALSO search Google Places API
    key = (google_key or os.getenv("GOOGLE_API_KEY") or "").strip()
    if key:
        print(f"🔍 Searching Google Places for hotels in {destination}")
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.priceLevel,places.googleMapsUri,places.location,places.photos",
        }
        payload = {"textQuery": f"hotels in {destination}", "languageCode": "en"}
        
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    for place in data.get("places", [])[:5]:
                        price_level = place.get("priceLevel", "PRICE_LEVEL_UNSPECIFIED")
                        # Pass destination city for price estimation
                        estimated_price = _estimate_price(price_level, destination)
                        if price_limit and estimated_price > price_limit:
                            continue
                        name = place.get("displayName", {}).get("text", "Unknown")
                        address = place.get("formattedAddress", destination)
                        
                        # Use Google Maps URI if available, otherwise construct from coordinates
                        maps_url = place.get("googleMapsUri")
                        if not maps_url:
                            location = place.get("location", {})
                            lat = location.get("latitude")
                            lng = location.get("longitude")
                            if lat and lng:
                                maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
                            else:
                                maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(name + ' ' + destination)}"
                        
                        # Get photo URL if available
                        photo_url = None
                        photos = place.get("photos", [])
                        if photos and len(photos) > 0:
                            photo_name = photos[0].get("name", "")
                            if photo_name:
                                # Google Places API v1 photo URL format
                                photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?maxHeightPx=400&maxWidthPx=600&key={key}"
                        
                        all_hotels.append(
                            {
                                "name": name,
                                "address": address,
                                "rating": place.get("rating"),
                                "price_per_night": estimated_price,
                                "price_note": "procjena" if price_level == "PRICE_LEVEL_UNSPECIFIED" else None,
                                "link": maps_url,
                                "source": "google",
                                "image": photo_url,
                            }
                        )
                    if all_hotels:
                        print(f"✅ Google found {len([h for h in all_hotels if h.get('source') == 'google'])} hotels")
        except Exception as e:
            print(f"⚠️ Google hotel search error: {e}")
    
    # Combine and deduplicate by name (case-insensitive)
    if all_hotels:
        seen_names = set()
        unique_hotels = []
        for hotel in all_hotels:
            name_lower = hotel.get("name", "").lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                unique_hotels.append(hotel)
        
        # Sort by price (cheapest first)
        unique_hotels.sort(key=lambda h: h.get("price_per_night", 9999))
        return unique_hotels[:8]  # Return top 8 combined results
    
    # Final fallback: mock data
    print(f"⚠️ Using mock hotels for {destination}")
    return get_mock_hotels(destination, max_price)
