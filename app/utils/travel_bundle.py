import json
import os
import re
from typing import Optional, Dict, Any, List
from urllib.parse import quote_plus

from .flights import search_flights, build_google_flights_link
from .hotels import search_hotels
from .categories import search_places
from .cards import build_card

try:
    from travel_planner import is_bus_route_possible, estimate_bus_duration
except Exception:  # pragma: no cover - fallback for stripped builds
    def is_bus_route_possible(origin: str, destination: str) -> bool:  # type: ignore
        return False

    def estimate_bus_duration(origin: str, destination: str, distance_km: Optional[int] = None) -> Optional[str]:  # type: ignore
        return None


def _slug_city(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9-]", "", value.strip().lower().replace(" ", "-"))


def _seeded_departure(origin: str, destination: str) -> str:
    seed = sum(ord(ch) for ch in (origin or "") + (destination or ""))
    hour = 6 + (seed % 9)
    minute = (seed // 7) % 4 * 15
    return f"{hour:02d}:{minute:02d}"


def _arrival_from_duration(departure: str, duration: Optional[str]) -> str:
    if not duration or "h" not in duration:
        return "same day"
    dep_parts = departure.split(":")
    dep_hour = int(dep_parts[0])
    dep_min = int(dep_parts[1])
    match = re.match(r"(\d+)h(?:\s*(\d+)m)?", duration)
    if not match:
        return "same day"
    hours = int(match.group(1))
    minutes = int(match.group(2) or 0)
    total_minutes = dep_hour * 60 + dep_min + hours * 60 + minutes
    arrival_hour = (total_minutes // 60) % 24
    arrival_min = total_minutes % 60
    day_increment = total_minutes // (24 * 60)
    suffix = "" if day_increment == 0 else f" (+{day_increment}d)"
    return f"{arrival_hour:02d}:{arrival_min:02d}{suffix}"


def _estimate_bus_price(origin: Optional[str], destination: Optional[str]) -> int:
    if not origin or not destination:
        return 40
    base = 30 + (len(origin) * 2 + len(destination))
    return max(25, min(180, base))


# City distance database (approximate km by car)
CITY_DISTANCES = {
    # Croatian cities (internal routes)
    ("zagreb", "rijeka"): 140,
    ("zagreb", "split"): 380,
    ("zagreb", "dubrovnik"): 600,
    ("zagreb", "osijek"): 280,
    ("zagreb", "zadar"): 285,
    ("zagreb", "pula"): 265,
    ("split", "dubrovnik"): 230,
    ("split", "zadar"): 150,
    ("rijeka", "pula"): 100,
    ("rijeka", "split"): 350,
    
    # Omišalj routes (island Krk, near Rijeka)
    ("omisalj", "rijeka"): 30,
    ("omišalj", "rijeka"): 30,
    ("omisalj", "zagreb"): 170,
    ("omišalj", "zagreb"): 170,
    ("omisalj", "budapest"): 520,
    ("omišalj", "budapest"): 520,
    ("omisalj", "budimpešta"): 520,
    ("omišalj", "budimpešta"): 520,
    ("omisalj", "vienna"): 450,
    ("omišalj", "vienna"): 450,
    ("omisalj", "beč"): 450,
    ("omišalj", "beč"): 450,
    ("omisalj", "ljubljana"): 140,
    ("omišalj", "ljubljana"): 140,
    ("omisalj", "trieste"): 100,
    ("omišalj", "trieste"): 100,
    ("omisalj", "trst"): 100,
    ("omišalj", "trst"): 100,
    
    # Slovenia
    ("zagreb", "ljubljana"): 140,
    ("rijeka", "ljubljana"): 120,
    
    # Budapest routes
    ("zagreb", "budapest"): 350,
    ("zagreb", "budimpešta"): 350,
    ("rijeka", "budapest"): 480,
    ("rijeka", "budimpešta"): 480,
    ("vienna", "budapest"): 240,
    ("beč", "budapest"): 240,
    ("bratislava", "budapest"): 200,
    
    # London routes
    ("rijeka", "london"): 1800,
    ("zagreb", "london"): 1750,
    ("split", "london"): 2100,
    ("ljubljana", "london"): 1600,
    ("paris", "london"): 450,
    ("berlin", "london"): 1100,
    ("amsterdam", "london"): 500,
    ("rome", "london"): 1900,
    ("barcelona", "london"): 1500,
    ("vienna", "london"): 1450,
    ("munich", "london"): 1100,
    ("prague", "london"): 1300,
    ("budapest", "london"): 1700,
    
    # Paris routes
    ("zagreb", "paris"): 1400,
    ("rijeka", "paris"): 1300,
    ("split", "paris"): 1600,
    
    # Croatia - Greece routes (CORRECTED distances)
    ("omisalj", "athens"): 1850,
    ("omisalj", "atena"): 1850,  # Croatian spelling
    ("omišalj", "athens"): 1850,
    ("omišalj", "atena"): 1850,
    ("rijeka", "athens"): 1850,
    ("rijeka", "atena"): 1850,
    ("zagreb", "athens"): 1600,
    ("zagreb", "atena"): 1600,
    ("split", "athens"): 1200,
    ("split", "atena"): 1200,
    ("dubrovnik", "athens"): 1100,
    ("dubrovnik", "atena"): 1100,
}

# Toll costs (approximate EUR for common routes)
TOLL_COSTS = {
    ("rijeka", "london"): 120,
    ("zagreb", "london"): 110,
    ("split", "london"): 130,
    ("zagreb", "paris"): 85,
    ("rijeka", "paris"): 80,
    ("split", "paris"): 95,
    ("paris", "london"): 30,
    ("ljubljana", "london"): 100,
    ("rome", "london"): 140,
    ("barcelona", "london"): 150,
    ("vienna", "london"): 95,
    ("munich", "london"): 70,
    ("prague", "london"): 85,
    ("budapest", "london"): 100,
    # Omišalj routes
    ("omisalj", "budapest"): 45,
    ("omišalj", "budapest"): 45,
    ("omisalj", "vienna"): 40,
    ("omišalj", "vienna"): 40,
    ("omisalj", "zagreb"): 15,
    ("omišalj", "zagreb"): 15,
    # Croatia - Greece tolls
    ("omisalj", "athens"): 75,
    ("omišalj", "athens"): 75,
    ("rijeka", "athens"): 75,
    ("zagreb", "athens"): 65,
    ("split", "athens"): 50,
    ("dubrovnik", "athens"): 40,
}

def _estimate_toll_cost(origin: Optional[str], destination: Optional[str]) -> int:
    """Estimate toll/highway costs in EUR"""
    if not origin or not destination:
        return 0
    
    origin_key = origin.lower().strip()
    dest_key = destination.lower().strip()
    
    # Check both directions
    if (origin_key, dest_key) in TOLL_COSTS:
        return TOLL_COSTS[(origin_key, dest_key)]
    if (dest_key, origin_key) in TOLL_COSTS:
        return TOLL_COSTS[(dest_key, origin_key)]
    
    # Fallback estimate based on distance
    distance = _estimate_driving_distance(origin, destination)
    if distance:
        return int(distance * 0.06)  # ~€0.06/km average toll
    return 50  # default fallback

def _build_google_maps_directions_link(origin: str, destination: str) -> str:
    """Build Google Maps directions link for driving route"""
    from urllib.parse import quote_plus
    origin_encoded = quote_plus(origin)
    dest_encoded = quote_plus(destination)
    return f"https://www.google.com/maps/dir/{origin_encoded}/{dest_encoded}/"


# Approximate coordinates for major cities (lat, lon)
CITY_COORDINATES = {
    # Americas
    "buenos aires": (-34.6, -58.4),
    "new york": (40.7, -74.0),
    "los angeles": (34.1, -118.2),
    "miami": (25.8, -80.2),
    "toronto": (43.7, -79.4),
    "mexico city": (19.4, -99.1),
    "sao paulo": (-23.5, -46.6),
    # Asia
    "tokyo": (35.7, 139.7),
    "beijing": (39.9, 116.4),
    "shanghai": (31.2, 121.5),
    "hong kong": (22.3, 114.2),
    "singapore": (1.3, 103.8),
    "bangkok": (13.8, 100.5),
    "seoul": (37.6, 127.0),
    "dubai": (25.3, 55.3),
    # Europe
    "paris": (48.9, 2.3),
    "london": (51.5, -0.1),
    "berlin": (52.5, 13.4),
    "rome": (41.9, 12.5),
    "madrid": (40.4, -3.7),
    "barcelona": (41.4, 2.2),
    "amsterdam": (52.4, 4.9),
    "vienna": (48.2, 16.4),
    "prague": (50.1, 14.4),
    "budapest": (47.5, 19.0),
    "munich": (48.1, 11.6),
    "zurich": (47.4, 8.5),
    "brussels": (50.8, 4.4),
    "athens": (37.98, 23.73),
    # Croatia & Region
    "zagreb": (45.8, 16.0),
    "rijeka": (45.3, 14.4),
    "split": (43.5, 16.4),
    "dubrovnik": (42.6, 18.1),
    "ljubljana": (46.1, 14.5),
    "bratislava": (48.1, 17.1),
    "belgrade": (44.8, 20.5),
}


def _calculate_distance_km(origin: str, destination: str) -> Optional[int]:
    """Calculate approximate distance between cities using coordinates (Haversine formula)"""
    import math
    
    origin_key = origin.lower().strip()
    dest_key = destination.lower().strip()
    
    # Try to find coordinates
    origin_coords = CITY_COORDINATES.get(origin_key)
    dest_coords = CITY_COORDINATES.get(dest_key)
    
    if not origin_coords or not dest_coords:
        return None
    
    # Haversine formula for distance between two points on Earth
    lat1, lon1 = math.radians(origin_coords[0]), math.radians(origin_coords[1])
    lat2, lon2 = math.radians(dest_coords[0]), math.radians(dest_coords[1])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth's radius in km
    r = 6371
    
    # Multiply by 1.3 for driving distance (roads aren't straight)
    return int(c * r * 1.3)


def _estimate_driving_distance(origin: Optional[str], destination: Optional[str]) -> Optional[int]:
    """Estimate driving distance in km between cities"""
    if not origin or not destination:
        return None
    
    # Normalize city names
    origin_key = origin.lower().strip()
    dest_key = destination.lower().strip()
    
    # Check both directions in database
    if (origin_key, dest_key) in CITY_DISTANCES:
        return CITY_DISTANCES[(origin_key, dest_key)]
    if (dest_key, origin_key) in CITY_DISTANCES:
        return CITY_DISTANCES[(dest_key, origin_key)]
    
    # Try coordinate-based calculation
    coord_distance = _calculate_distance_km(origin, destination)
    if coord_distance:
        return coord_distance
    
    # Return None if we can't estimate - DON'T make up numbers!
    return None


def _is_driving_possible(origin: Optional[str], destination: Optional[str]) -> bool:
    """Check if driving is physically possible between two locations (same continent, no oceans)"""
    if not origin or not destination:
        return False
    
    origin_key = origin.lower().strip()
    dest_key = destination.lower().strip()
    
    # Skip generic/invalid destinations
    invalid_destinations = {"go to", "somewhere", "anywhere", "unknown", ""}
    if origin_key in invalid_destinations or dest_key in invalid_destinations:
        return False
    
    # Define cities that are DEFINITELY in Americas (across ocean from Europe)
    americas = {"buenos aires", "new york", "los angeles", "miami", "toronto", "mexico city", "sao paulo", 
                "chicago", "boston", "washington", "san francisco", "vancouver", "rio de janeiro",
                "seattle", "denver", "atlanta", "houston", "dallas", "phoenix", "philadelphia",
                "montreal", "calgary", "lima", "bogota", "santiago", "caracas", "havana"}
    
    # Define cities that are DEFINITELY in Asia/Pacific (across ocean from Europe)
    asia_pacific = {"tokyo", "beijing", "shanghai", "hong kong", "singapore", "bangkok", "seoul", 
                    "osaka", "kyoto", "taipei", "manila", "kuala lumpur", "jakarta", "sydney", "melbourne",
                    "auckland", "wellington", "perth", "brisbane", "hanoi", "ho chi minh", "mumbai",
                    "delhi", "bangalore", "chennai", "kolkata", "karachi", "dhaka"}
    
    # Check if either city is in Americas or Asia (cross-oceanic)
    origin_in_americas = origin_key in americas
    origin_in_asia = origin_key in asia_pacific
    dest_in_americas = dest_key in americas
    dest_in_asia = dest_key in asia_pacific
    
    # Cross-continental = impossible to drive (ocean in between)
    if origin_in_americas and (dest_in_asia or (not dest_in_americas)):
        # Origin in Americas, destination NOT in Americas = ocean
        if not dest_in_americas:
            print(f"🚫 Cross-oceanic: {origin} (Americas) → {destination} (other continent)")
            return False
    
    if origin_in_asia and (dest_in_americas or (not dest_in_asia)):
        # Origin in Asia, destination NOT in Asia = ocean
        if not dest_in_asia:
            print(f"🚫 Cross-oceanic: {origin} (Asia) → {destination} (other continent)")
            return False
    
    if dest_in_americas and not origin_in_americas:
        print(f"🚫 Cross-oceanic: {origin} → {destination} (Americas)")
        return False
        
    if dest_in_asia and not origin_in_asia:
        print(f"🚫 Cross-oceanic: {origin} → {destination} (Asia)")
        return False
    
    # If neither city is in Americas or Asia, assume they're both in Europe/Middle East
    # and driving IS possible (even for unknown small towns like Omišalj)
    print(f"✅ Driving possible: {origin} → {destination} (assumed same landmass)")
    return True


def _should_search_flights(origin: Optional[str], destination: Optional[str]) -> bool:
    """
    Decide if flights make sense for this route.
    Skip flights for short distances (<200km) where car/bus is more practical.
    """
    if not origin or not destination:
        return False
    
    distance = _estimate_driving_distance(origin, destination)
    
    # Don't search flights for short distances (<200km)
    # Examples: Rijeka-Zagreb (140km), Zagreb-Ljubljana (140km)
    if distance and distance < 200:
        print(f"⏭️ Skipping flight search for {origin}→{destination} ({distance}km - too short)")
        return False
    
    # Always search flights for long distances (>500km)
    if distance and distance > 500:
        return True
    
    # For medium distances (200-500km), search flights
    return True


# Import smart distance module for intelligent driving calculations
from .smart_distance import (
    build_smart_driving_option,
    get_driving_distance,
    is_driving_possible as smart_is_driving_possible,
    geocode_city,
)


async def _build_driving_option_async(origin: Optional[str], destination: Optional[str], google_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Build driving/car transport option using smart distance calculation (works for ANY city!)"""
    if not origin or not destination:
        return None
    
    # Use the smart system that works for any city
    result = await build_smart_driving_option(origin, destination, google_key)
    
    if result is None:
        print(f"🚫 Driving not possible: {origin} → {destination}")
    
    return result


def _build_driving_option(origin: Optional[str], destination: Optional[str]) -> Optional[Dict[str, Any]]:
    """Sync wrapper for backward compatibility - uses hardcoded data"""
    if not origin or not destination:
        return None
    
    # Check if driving is physically possible (same continent)
    if not _is_driving_possible(origin, destination):
        print(f"🚫 Driving not possible: {origin} → {destination} (cross-continental)")
        return None
    
    distance_km = _estimate_driving_distance(origin, destination)
    if not distance_km:
        print(f"⚠️ Cannot estimate driving distance: {origin} → {destination}")
        return None
    
    # Estimate driving time (rough: 80 km/h average including breaks)
    drive_hours = distance_km / 80
    
    # Fuel cost estimate (rough: 7L/100km diesel, €1.60/L)
    fuel_cost = int((distance_km / 100) * 7 * 1.60)
    
    # Toll/highway costs
    toll_cost = _estimate_toll_cost(origin, destination)
    
    # Total cost (fuel + tolls)
    total_cost = fuel_cost + toll_cost
    
    # Recommend split if > 10 hours
    days_recommended = 2 if drive_hours > 10 else 1
    duration_text = f"{int(drive_hours)}h" if drive_hours < 10 else f"{int(drive_hours)}h (preporučeno {days_recommended} dana)"
    
    # Google Maps directions link
    maps_link = _build_google_maps_directions_link(origin, destination)
    
    return {
        "mode": "car",
        "distance_km": distance_km,
        "duration": duration_text,
        "fuel_cost": fuel_cost,
        "toll_cost": toll_cost,
        "total_cost": total_cost,
        "days_recommended": days_recommended,
        "link": maps_link,
        "notes": "Ruta vodi preko prekrasnih alpskih krajolika" if distance_km > 1000 else "Kratka vožnja autom"
    }


# Direct bus routes that actually exist (FlixBus network)
DIRECT_BUS_ROUTES = {
    # Croatia - Western Europe
    ("zagreb", "munich"), ("zagreb", "vienna"), ("zagreb", "budapest"), ("zagreb", "berlin"),
    ("zagreb", "paris"), ("zagreb", "amsterdam"), ("zagreb", "prague"),
    ("split", "munich"), ("split", "vienna"), ("split", "budapest"),
    ("rijeka", "munich"), ("rijeka", "vienna"), ("rijeka", "trieste"), ("rijeka", "budapest"),
    ("dubrovnik", "munich"), ("dubrovnik", "vienna"),
    # Major European routes
    ("paris", "london"), ("paris", "amsterdam"), ("paris", "brussels"), ("paris", "berlin"),
    ("berlin", "amsterdam"), ("berlin", "prague"), ("berlin", "vienna"), ("berlin", "warsaw"),
    ("munich", "vienna"), ("munich", "prague"), ("munich", "zurich"),
    ("vienna", "budapest"), ("vienna", "prague"), ("vienna", "bratislava"),
    # Balkan routes
    ("zagreb", "sarajevo"), ("zagreb", "belgrade"), ("zagreb", "ljubljana"),
    ("split", "sarajevo"), ("split", "mostar"),
    ("rijeka", "ljubljana"), ("rijeka", "zagreb"),
    ("dubrovnik", "mostar"), ("dubrovnik", "split"),
}


def _is_direct_bus_available(origin: str, destination: str) -> bool:
    """Check if direct bus route exists between two cities"""
    origin_norm = origin.lower().strip()
    dest_norm = destination.lower().strip()
    
    # Check both directions
    return ((origin_norm, dest_norm) in DIRECT_BUS_ROUTES or 
            (dest_norm, origin_norm) in DIRECT_BUS_ROUTES)
TRANSPORT_HUBS = {
    "croatia": ["zagreb", "rijeka", "split", "dubrovnik", "zadar", "osijek", "pula"],
    "slovenia": ["ljubljana", "maribor"],
    "bosnia": ["sarajevo", "mostar", "banja luka"],
    "serbia": ["belgrade", "novi sad"],
    "greece": ["athens", "thessaloniki"],
}

# Small towns mapped to nearest hub
TOWN_TO_HUB = {
    "omisalj": "rijeka",
    "icici": "rijeka",
    "opatija": "rijeka",
    "crikvenica": "rijeka",
    "mali losinj": "rijeka",
    "krk": "rijeka",
    "cres": "rijeka",
    "vrbnik": "rijeka",
    "punat": "rijeka",
    "baska": "rijeka",
    "makarska": "split",
    "trogir": "split",
    "omis": "split",
    "hvar": "split",
    "brac": "split",
    "vis": "split",
    "korcula": "dubrovnik",
    "mljet": "dubrovnik",
    "cavtat": "dubrovnik",
}


def _find_nearest_hub(city: Optional[str]) -> Optional[str]:
    """Find nearest major transport hub for a city"""
    if not city:
        return None
    
    city_normalized = city.lower().strip()
    
    # Check if it's already a hub
    for hubs in TRANSPORT_HUBS.values():
        if city_normalized in hubs:
            return city_normalized
    
    # Check if mapped to a hub
    if city_normalized in TOWN_TO_HUB:
        return TOWN_TO_HUB[city_normalized]
    
    # Default fallback - return None (no hub found)
    return None


def _build_bus_options(origin: Optional[str], destination: Optional[str]) -> List[Dict[str, Any]]:
    """Build bus options with smart multi-segment routing via hubs if needed"""
    if not origin or not destination:
        return []
    
    origin_normalized = origin.lower().strip()
    dest_normalized = destination.lower().strip()
    
    # Check if direct route EXISTS (not just geographically possible)
    if _is_direct_bus_available(origin_normalized, dest_normalized):
        # Direct route exists
        duration = estimate_bus_duration(origin, destination) or "10h"
        departure = _seeded_departure(origin, destination)
        arrival = _arrival_from_duration(departure, duration)
        slug_origin = _slug_city(origin)
        slug_destination = _slug_city(destination)
        link = f"https://www.rome2rio.com/s/{slug_origin}/{slug_destination}"
        
        return [
            {
                "company": "FlixBus",
                "route": f"{origin.title()} → {destination.title()}",
                "departure": departure,
                "arrival": arrival,
                "duration": duration,
                "price": _estimate_bus_price(origin, destination),
                "link": link,
                "segments": 1,
            }
        ]
    
    # No direct route - find multi-segment via hub
    origin_hub = _find_nearest_hub(origin)
    dest_hub = _find_nearest_hub(destination)
    
    if not origin_hub:
        # Origin is small town without mapped hub - return Rome2Rio general link
        rome2rio_link = f"https://www.rome2rio.com/s/{_slug_city(origin)}/{_slug_city(destination)}"
        return [
            {
                "company": "Rome2Rio",
                "route": f"{origin.title()} → {destination.title()}",
                "departure": "Provjeri Rome2Rio",
                "arrival": "—",
                "duration": "—",
                "price": None,
                "link": rome2rio_link,
                "segments": 0,
                "note": f"Nema direktnog busa. Koristi Rome2Rio za pronalaženje rute preko {origin_hub or 'najbližeg grada'}.",
            }
        ]
    
    # Build multi-segment route: origin → hub → destination
    buses = []
    
    # Segment 1: Small town → Hub (local bus)
    if origin_normalized != origin_hub:
        local_duration = "30 min" if origin_hub == "rijeka" else "45 min"
        local_price = 5 if origin_hub == "rijeka" else 8
        buses.append({
            "company": "Lokalni prijevoz",
            "route": f"{origin.title()} → {origin_hub.title()}",
            "departure": "08:00",
            "arrival": "08:30" if origin_hub == "rijeka" else "08:45",
            "duration": local_duration,
            "price": local_price,
            "link": f"https://www.rome2rio.com/s/{_slug_city(origin)}/{_slug_city(origin_hub)}",
            "segments": 1,
            "note": f"Lokalni bus ili autotrola do {origin_hub.title()}",
        })
    
    # Segment 2: Hub → Destination (FlixBus/long-distance)
    if _is_direct_bus_available(origin_hub, dest_normalized):
        duration = estimate_bus_duration(origin_hub, destination) or "15h"
        long_distance_price = _estimate_bus_price(origin_hub, destination)
        buses.append({
            "company": "FlixBus",
            "route": f"{origin_hub.title()} → {destination.title()}",
            "departure": "10:00",
            "arrival": _arrival_from_duration("10:00", duration),
            "duration": duration,
            "price": long_distance_price,
            "link": f"https://www.rome2rio.com/s/{_slug_city(origin_hub)}/{_slug_city(destination)}",
            "segments": 2,
            "note": f"Glavni bus od {origin_hub.title()} do destinacije",
        })
    else:
        # Even hub doesn't have direct - use Rome2Rio
        rome2rio_link = f"https://www.rome2rio.com/s/{_slug_city(origin_hub)}/{_slug_city(destination)}"
        buses.append({
            "company": "Rome2Rio",
            "route": f"{origin_hub.title()} → {destination.title()}",
            "departure": "Provjeri Rome2Rio",
            "arrival": "—",
            "duration": "—",
            "price": None,
            "link": rome2rio_link,
            "segments": 2,
            "note": f"Koristi Rome2Rio za pronalaženje najbolje rute preko {origin_hub.title()}",
        })
    
    return buses


def _build_train_options(origin: Optional[str], destination: Optional[str], rome2rio_link: str) -> List[Dict[str, Any]]:
    if not origin or not destination:
        return []
    duration = estimate_bus_duration(origin, destination)
    if duration:
        duration = duration.replace("h", "h (overnight)")
    operator = "Railjet" if len(destination) % 2 == 0 else "EuroNight"
    return [
        {
            "operator": operator,
            "departure": "21:10",
            "arrival": "07:05 (+1d)",
            "duration": duration or "Overnight",
            "price": max(35, min(150, _estimate_bus_price(origin, destination) + 15)),
            "link": rome2rio_link,
        }
    ]


async def build_travel_bundle(
    origin: Optional[str],
    destination: str,
    api_keys: Dict[str, Optional[str]],
    budget: Optional[int],
    language_code: str,
    travel_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    api_keys = api_keys or {}
    context = travel_context or {}
    resolved_origin = origin or context.get("origin") or None
    effective_budget = budget or context.get("budget")
    
    # Extract dates from context
    departure_date = context.get("departure_date")
    return_date = context.get("return_date")
    
    # Search flights ONLY if distance makes sense (skip for short routes like Rijeka-Zagreb)
    flights = []
    if _should_search_flights(resolved_origin, destination):
        flights = await search_flights(
            resolved_origin, 
            destination, 
            effective_budget, 
            departure_date,
            return_date
        )
    
    google_key = api_keys.get("google")
    
    # Search hotels with dates (Amadeus + Google fallback)
    hotels = await search_hotels(
        destination, 
        google_key, 
        effective_budget,
        check_in_date=departure_date,
        check_out_date=return_date
    )
    
    restaurants = await search_places("best restaurants", destination, 4, language_code, google_key)
    activities = await search_places("things to do", destination, 4, language_code, google_key)
    buses = _build_bus_options(resolved_origin, destination)
    rome2rio_link = (
        f"https://www.rome2rio.com/s/{_slug_city(resolved_origin or destination)}/{_slug_city(destination)}"
        if destination
        else "https://www.rome2rio.com/"
    )
    trains = _build_train_options(resolved_origin, destination, rome2rio_link)
    
    # Use smart async driving calculation that works for ANY city!
    google_key = api_keys.get("google") or os.getenv("GOOGLE_API_KEY")
    driving = await _build_driving_option_async(resolved_origin, destination, google_key)
    origin_for_links = resolved_origin or destination or ""
    
    links = {
        "google_flights": build_google_flights_link(origin_for_links, destination),
        "booking": f"https://www.booking.com/searchresults.html?ss={quote_plus(destination)}",
        "airbnb": f"https://www.airbnb.com/s/{quote_plus(destination)}--stays",
        "rome2rio": rome2rio_link,
        "train": rome2rio_link,
    }
    
    return {
        "origin": resolved_origin,
        "destination": destination,
        "budget": effective_budget,
        "trip_dates": context.get("dates"),
        "departure_date": departure_date,
        "return_date": return_date,
        "preferences": context.get("preferences") or context.get("interests") or [],
        "notes": context.get("notes"),
        "driving": driving,
        "flights": flights,
        "buses": buses,
        "trains": trains,
        "hotels": hotels,
        "restaurants": restaurants,
        "activities": activities,
        "links": links,
        "meta": {
            "needs_flights": context.get("needs_flights"),
            "needs_accommodation": context.get("needs_accommodation"),
            "language_code": language_code,
        },
    }


async def build_return_bundle(
    origin: str,
    destination: str,
    api_keys: Dict[str, Optional[str]],
    budget: Optional[int],
    language_code: str,
    travel_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a return trip bundle with ONLY transportation options.
    No hotels, no activities, no restaurants - just ways to get back home.
    
    Args:
        origin: Return trip origin (where user is traveling FROM back home)
        destination: Return trip destination (where user wants to go back TO)
        api_keys: API keys dict
        budget: Optional budget constraint
        language_code: User's language
        travel_context: Optional context with dates/preferences
    
    Returns:
        Bundle with only transportation options (flights, buses, trains, driving)
    """
    api_keys = api_keys or {}
    context = travel_context or {}
    effective_budget = budget or context.get("budget")
    
    # Extract return date (or departure date if this is explicit return trip)
    return_date = context.get("return_date")
    departure_date = context.get("departure_date")  # May be used as return trip date
    
    # Search flights for return trip (origin and destination are SWAPPED)
    flights = await search_flights(
        origin,  # Traveling FROM destination back TO origin
        destination,
        effective_budget,
        departure_date=return_date or departure_date,  # Use return date if available
        return_date=None  # One-way return trip
    )
    
    # Build other transport options (buses, trains, driving)
    buses = _build_bus_options(origin, destination)
    
    rome2rio_link = (
        f"https://www.rome2rio.com/s/{_slug_city(origin)}/{_slug_city(destination)}"
        if destination
        else "https://www.rome2rio.com/"
    )
    
    trains = _build_train_options(origin, destination, rome2rio_link)
    
    # Use smart async driving calculation
    google_key = api_keys.get("google") or os.getenv("GOOGLE_API_KEY")
    driving = await _build_driving_option_async(origin, destination, google_key)
    
    links = {
        "google_flights": build_google_flights_link(origin, destination),
        "rome2rio": rome2rio_link,
        "train": rome2rio_link,
    }
    
    return {
        "origin": origin,
        "destination": destination,
        "budget": effective_budget,
        "return_date": return_date or departure_date,
        "is_return_trip": True,  # Flag to identify this as return journey
        "driving": driving,
        "flights": flights,
        "buses": buses,
        "trains": trains,
        "links": links,
        # NO hotels, restaurants, activities for return trips
        "meta": {
            "language_code": language_code,
            "trip_type": "return",
        },
    }


def cards_from_bundle(bundle: Dict[str, Any]) -> str:
    destination = bundle.get("destination") or "Unknown"
    cards: List[str] = []
    for flight in bundle.get("flights", [])[:2]:
        cards.append(
            build_card(
                "flight",
                f"{flight.get('airline', 'Flight')} {flight.get('price', '')}",
                destination,
                f"Departure {flight.get('departure_date', '?')} · Duration {flight.get('duration', '?')}",
                flight.get("link", bundle["links"].get("google_flights", "https://google.com")),
            )
        )
    for hotel in bundle.get("hotels", [])[:3]:
        cards.append(
            build_card(
                "hotel",
                hotel.get("name", "Hotel"),
                destination,
                f"€{hotel.get('price_per_night', '?')}/night · ⭐ {hotel.get('rating', '?')}",
                hotel.get("link", bundle["links"].get("booking", "https://booking.com")),
            )
        )
    for place in bundle.get("restaurants", [])[:3]:
        cards.append(
            build_card(
                "restaurant",
                place.get("name", "Restaurant"),
                destination,
                place.get("address", "Local favorite"),
                place.get("maps_url", "https://maps.google.com"),
            )
        )
    for activity in bundle.get("activities", [])[:3]:
        cards.append(
            build_card(
                "activity",
                activity.get("name", "Activity"),
                destination,
                activity.get("address", "Must-see spot"),
                activity.get("maps_url", "https://maps.google.com"),
            )
        )
    return "\n".join(cards)


def serialize_bundle(bundle: Dict[str, Any]) -> str:
    return json.dumps(bundle, ensure_ascii=False)
