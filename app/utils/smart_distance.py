"""
Smart Distance Calculator - Works for ANY city in the world!

Uses:
1. Google Maps Distance Matrix API for accurate driving distances
2. Google Geocoding API to detect continent/country
3. Haversine formula as fallback
4. Intelligent caching to avoid repeated API calls
"""

import os
import math
import asyncio
from typing import Optional, Dict, Tuple, Any
from functools import lru_cache

import httpx

# Cache for geocoded cities (continent, country, coordinates)
_geocode_cache: Dict[str, Dict[str, Any]] = {}

# Cache for distances between city pairs
_distance_cache: Dict[Tuple[str, str], Optional[int]] = {}


# Continent definitions based on country
COUNTRY_TO_CONTINENT = {
    # Americas
    "united states": "americas", "usa": "americas", "canada": "americas", "mexico": "americas",
    "brazil": "americas", "argentina": "americas", "chile": "americas", "colombia": "americas",
    "peru": "americas", "venezuela": "americas", "cuba": "americas", "ecuador": "americas",
    "guatemala": "americas", "bolivia": "americas", "dominican republic": "americas",
    "honduras": "americas", "paraguay": "americas", "el salvador": "americas",
    "nicaragua": "americas", "costa rica": "americas", "panama": "americas", "uruguay": "americas",
    "puerto rico": "americas", "jamaica": "americas", "haiti": "americas", "bahamas": "americas",
    
    # Europe (including UK post-Brexit)
    "croatia": "europe", "hrvatska": "europe",
    "slovenia": "europe", "slovenija": "europe",
    "austria": "europe", "germany": "europe", "deutschland": "europe",
    "france": "europe", "italy": "europe", "italia": "europe",
    "spain": "europe", "españa": "europe", "portugal": "europe",
    "united kingdom": "europe", "uk": "europe", "england": "europe", "scotland": "europe", "wales": "europe",
    "ireland": "europe", "netherlands": "europe", "belgium": "europe",
    "switzerland": "europe", "poland": "europe", "polska": "europe",
    "czech republic": "europe", "czechia": "europe",
    "hungary": "europe", "magyarország": "europe",
    "romania": "europe", "bulgaria": "europe",
    "greece": "europe", "sweden": "europe", "norway": "europe",
    "finland": "europe", "denmark": "europe", "iceland": "europe",
    "serbia": "europe", "srbija": "europe",
    "bosnia and herzegovina": "europe", "bosnia": "europe",
    "montenegro": "europe", "north macedonia": "europe", "macedonia": "europe",
    "albania": "europe", "kosovo": "europe",
    "slovakia": "europe", "lithuania": "europe", "latvia": "europe", "estonia": "europe",
    "luxembourg": "europe", "malta": "europe", "cyprus": "europe",
    "ukraine": "europe", "belarus": "europe", "moldova": "europe",
    "turkey": "europe",  # Transcontinental, but drivable from Europe
    
    # Asia
    "japan": "asia", "china": "asia", "south korea": "asia", "north korea": "asia",
    "india": "asia", "indonesia": "asia", "pakistan": "asia", "bangladesh": "asia",
    "vietnam": "asia", "thailand": "asia", "philippines": "asia", "malaysia": "asia",
    "singapore": "asia", "myanmar": "asia", "cambodia": "asia", "laos": "asia",
    "nepal": "asia", "sri lanka": "asia", "taiwan": "asia", "mongolia": "asia",
    "kazakhstan": "asia", "uzbekistan": "asia", "iran": "asia", "iraq": "asia",
    "saudi arabia": "asia", "united arab emirates": "asia", "uae": "asia",
    "israel": "asia", "jordan": "asia", "lebanon": "asia", "syria": "asia",
    "qatar": "asia", "kuwait": "asia", "bahrain": "asia", "oman": "asia", "yemen": "asia",
    "afghanistan": "asia", "turkmenistan": "asia", "tajikistan": "asia", "kyrgyzstan": "asia",
    
    # Oceania
    "australia": "oceania", "new zealand": "oceania", "fiji": "oceania",
    "papua new guinea": "oceania",
    
    # Africa
    "egypt": "africa", "south africa": "africa", "nigeria": "africa", "kenya": "africa",
    "morocco": "africa", "algeria": "africa", "tunisia": "africa", "libya": "africa",
    "ethiopia": "africa", "ghana": "africa", "tanzania": "africa", "uganda": "africa",
    "sudan": "africa", "angola": "africa", "mozambique": "africa", "madagascar": "africa",
    "cameroon": "africa", "ivory coast": "africa", "senegal": "africa", "zimbabwe": "africa",
    "zambia": "africa", "botswana": "africa", "namibia": "africa", "rwanda": "africa",
    
    # Russia - transcontinental, but Moscow/St Petersburg are in Europe
    "russia": "europe",  # Default to Europe for major cities
}

# Continents that CAN be driven between (connected by land)
DRIVABLE_CONTINENT_PAIRS = {
    ("europe", "europe"),
    ("europe", "africa"),  # Via Morocco-Spain ferry or Egypt-Israel
    ("africa", "africa"),
    ("americas", "americas"),
    ("asia", "asia"),
    # Europe-Asia is drivable through Turkey/Russia
    ("europe", "asia"),
    ("asia", "europe"),
}


async def geocode_city(city: str, google_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Get city coordinates, country, and continent using Google Geocoding API.
    Returns: {"lat": float, "lng": float, "country": str, "continent": str}
    """
    city_key = city.lower().strip()
    
    # Check cache first
    if city_key in _geocode_cache:
        return _geocode_cache[city_key]
    
    key = (google_key or os.getenv("GOOGLE_API_KEY") or "").strip()
    
    result = {
        "lat": None,
        "lng": None,
        "country": None,
        "continent": "unknown"
    }
    
    if not key:
        # Fallback: Try to guess from hardcoded data
        result = _fallback_geocode(city_key)
        _geocode_cache[city_key] = result
        return result
    
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": city,
            "key": key,
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            data = response.json()
        
        if data.get("status") == "OK" and data.get("results"):
            place = data["results"][0]
            
            # Get coordinates
            location = place.get("geometry", {}).get("location", {})
            result["lat"] = location.get("lat")
            result["lng"] = location.get("lng")
            
            # Get country from address components
            for component in place.get("address_components", []):
                if "country" in component.get("types", []):
                    country_name = component.get("long_name", "").lower()
                    result["country"] = country_name
                    result["continent"] = COUNTRY_TO_CONTINENT.get(country_name, "unknown")
                    break
            
            print(f"📍 Geocoded {city}: {result['country']} ({result['continent']})")
    
    except Exception as e:
        print(f"⚠️ Geocoding failed for {city}: {e}")
        result = _fallback_geocode(city_key)
    
    _geocode_cache[city_key] = result
    return result


def _fallback_geocode(city_key: str) -> Dict[str, Any]:
    """Fallback geocoding using hardcoded data"""
    # Known cities with coordinates and countries
    KNOWN_CITIES = {
        # Croatia
        "zagreb": (45.8, 16.0, "croatia"),
        "rijeka": (45.3, 14.4, "croatia"),
        "split": (43.5, 16.4, "croatia"),
        "dubrovnik": (42.6, 18.1, "croatia"),
        "zadar": (44.1, 15.2, "croatia"),
        "pula": (44.9, 13.8, "croatia"),
        "osijek": (45.6, 18.7, "croatia"),
        "opatija": (45.3, 14.3, "croatia"),
        "omisalj": (45.2, 14.5, "croatia"),
        "omišalj": (45.2, 14.5, "croatia"),
        "krk": (45.0, 14.6, "croatia"),
        "crikvenica": (45.2, 14.7, "croatia"),
        "mali lošinj": (44.5, 14.5, "croatia"),
        "rovinj": (45.1, 13.6, "croatia"),
        "poreč": (45.2, 13.6, "croatia"),
        "makarska": (43.3, 17.0, "croatia"),
        "šibenik": (43.7, 15.9, "croatia"),
        
        # Slovenia
        "ljubljana": (46.1, 14.5, "slovenia"),
        "maribor": (46.6, 15.6, "slovenia"),
        "koper": (45.5, 13.7, "slovenia"),
        "bled": (46.4, 14.1, "slovenia"),
        
        # Austria
        "vienna": (48.2, 16.4, "austria"),
        "beč": (48.2, 16.4, "austria"),
        "wien": (48.2, 16.4, "austria"),
        "salzburg": (47.8, 13.0, "austria"),
        "graz": (47.1, 15.4, "austria"),
        "innsbruck": (47.3, 11.4, "austria"),
        
        # Hungary
        "budapest": (47.5, 19.0, "hungary"),
        "budimpešta": (47.5, 19.0, "hungary"),
        
        # Italy
        "rome": (41.9, 12.5, "italy"),
        "rim": (41.9, 12.5, "italy"),
        "milan": (45.5, 9.2, "italy"),
        "milano": (45.5, 9.2, "italy"),
        "venice": (45.4, 12.3, "italy"),
        "venecija": (45.4, 12.3, "italy"),
        "florence": (43.8, 11.3, "italy"),
        "firenca": (43.8, 11.3, "italy"),
        "naples": (40.9, 14.3, "italy"),
        "napulj": (40.9, 14.3, "italy"),
        "trieste": (45.6, 13.8, "italy"),
        "trst": (45.6, 13.8, "italy"),
        
        # Germany
        "berlin": (52.5, 13.4, "germany"),
        "munich": (48.1, 11.6, "germany"),
        "minhen": (48.1, 11.6, "germany"),
        "münchen": (48.1, 11.6, "germany"),
        "frankfurt": (50.1, 8.7, "germany"),
        "hamburg": (53.6, 10.0, "germany"),
        "cologne": (50.9, 7.0, "germany"),
        "köln": (50.9, 7.0, "germany"),
        
        # France
        "paris": (48.9, 2.3, "france"),
        "pariz": (48.9, 2.3, "france"),
        "nice": (43.7, 7.3, "france"),
        "nica": (43.7, 7.3, "france"),
        "lyon": (45.8, 4.8, "france"),
        "marseille": (43.3, 5.4, "france"),
        
        # UK
        "london": (51.5, -0.1, "united kingdom"),
        "manchester": (53.5, -2.2, "united kingdom"),
        "birmingham": (52.5, -1.9, "united kingdom"),
        "edinburgh": (56.0, -3.2, "united kingdom"),
        "glasgow": (55.9, -4.3, "united kingdom"),
        
        # Spain
        "madrid": (40.4, -3.7, "spain"),
        "barcelona": (41.4, 2.2, "spain"),
        
        # Other Europe
        "amsterdam": (52.4, 4.9, "netherlands"),
        "brussels": (50.8, 4.4, "belgium"),
        "bruxelles": (50.8, 4.4, "belgium"),
        "prague": (50.1, 14.4, "czech republic"),
        "prag": (50.1, 14.4, "czech republic"),
        "warsaw": (52.2, 21.0, "poland"),
        "varšava": (52.2, 21.0, "poland"),
        "bratislava": (48.1, 17.1, "slovakia"),
        "zurich": (47.4, 8.5, "switzerland"),
        "zürich": (47.4, 8.5, "switzerland"),
        "geneva": (46.2, 6.1, "switzerland"),
        "athens": (37.98, 23.73, "greece"),
        "atena": (37.98, 23.73, "greece"),
        "lisbon": (38.7, -9.1, "portugal"),
        "lisabon": (38.7, -9.1, "portugal"),
        "dublin": (53.3, -6.3, "ireland"),
        "copenhagen": (55.7, 12.6, "denmark"),
        "stockholm": (59.3, 18.1, "sweden"),
        "oslo": (59.9, 10.7, "norway"),
        "helsinki": (60.2, 24.9, "finland"),
        
        # Balkans
        "belgrade": (44.8, 20.5, "serbia"),
        "beograd": (44.8, 20.5, "serbia"),
        "sarajevo": (43.9, 18.4, "bosnia and herzegovina"),
        "skopje": (42.0, 21.4, "north macedonia"),
        "tirana": (41.3, 19.8, "albania"),
        "podgorica": (42.4, 19.3, "montenegro"),
        
        # Americas
        "new york": (40.7, -74.0, "united states"),
        "los angeles": (34.1, -118.2, "united states"),
        "chicago": (41.9, -87.6, "united states"),
        "miami": (25.8, -80.2, "united states"),
        "san francisco": (37.8, -122.4, "united states"),
        "boston": (42.4, -71.1, "united states"),
        "washington": (38.9, -77.0, "united states"),
        "seattle": (47.6, -122.3, "united states"),
        "toronto": (43.7, -79.4, "canada"),
        "vancouver": (49.3, -123.1, "canada"),
        "montreal": (45.5, -73.6, "canada"),
        "mexico city": (19.4, -99.1, "mexico"),
        "buenos aires": (34.6, -58.4, "argentina"),
        "sao paulo": (-23.5, -46.6, "brazil"),
        "rio de janeiro": (-22.9, -43.2, "brazil"),
        
        # Asia
        "tokyo": (35.7, 139.7, "japan"),
        "beijing": (39.9, 116.4, "china"),
        "peking": (39.9, 116.4, "china"),
        "shanghai": (31.2, 121.5, "china"),
        "hong kong": (22.3, 114.2, "china"),
        "singapore": (1.3, 103.8, "singapore"),
        "bangkok": (13.8, 100.5, "thailand"),
        "seoul": (37.6, 127.0, "south korea"),
        "dubai": (25.3, 55.3, "united arab emirates"),
        "mumbai": (19.1, 72.9, "india"),
        "delhi": (28.6, 77.2, "india"),
        
        # Oceania
        "sydney": (-33.9, 151.2, "australia"),
        "melbourne": (-37.8, 145.0, "australia"),
        "auckland": (-36.8, 174.8, "new zealand"),
    }
    
    if city_key in KNOWN_CITIES:
        lat, lng, country = KNOWN_CITIES[city_key]
        continent = COUNTRY_TO_CONTINENT.get(country, "unknown")
        return {"lat": lat, "lng": lng, "country": country, "continent": continent}
    
    return {"lat": None, "lng": None, "country": None, "continent": "unknown"}


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Calculate distance between two points using Haversine formula (returns km)"""
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    # Multiply by 1.3 for road distance estimate (roads aren't straight lines)
    return int(R * c * 1.3)


async def get_driving_distance(origin: str, destination: str, google_key: Optional[str] = None) -> Optional[int]:
    """
    Get driving distance between two cities using Google Distance Matrix API.
    Falls back to Haversine calculation if API unavailable.
    Returns distance in km, or None if route impossible.
    """
    cache_key = (origin.lower().strip(), destination.lower().strip())
    
    # Check cache
    if cache_key in _distance_cache:
        return _distance_cache[cache_key]
    
    key = (google_key or os.getenv("GOOGLE_API_KEY") or "").strip()
    
    # First check if driving is even possible (same continent)
    origin_geo = await geocode_city(origin, key)
    dest_geo = await geocode_city(destination, key)
    
    origin_continent = origin_geo.get("continent", "unknown")
    dest_continent = dest_geo.get("continent", "unknown")
    
    # Check if cross-oceanic (not drivable)
    continent_pair = (origin_continent, dest_continent)
    if continent_pair not in DRIVABLE_CONTINENT_PAIRS and (dest_continent, origin_continent) not in DRIVABLE_CONTINENT_PAIRS:
        print(f"🚫 Driving impossible: {origin} ({origin_continent}) → {destination} ({dest_continent})")
        _distance_cache[cache_key] = None
        return None
    
    # Try Google Distance Matrix API
    if key:
        try:
            url = "https://maps.googleapis.com/maps/api/distancematrix/json"
            params = {
                "origins": origin,
                "destinations": destination,
                "mode": "driving",
                "key": key,
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params)
                data = response.json()
            
            if data.get("status") == "OK":
                rows = data.get("rows", [])
                if rows and rows[0].get("elements"):
                    element = rows[0]["elements"][0]
                    if element.get("status") == "OK":
                        distance_m = element.get("distance", {}).get("value", 0)
                        distance_km = int(distance_m / 1000)
                        print(f"📏 Google Distance: {origin} → {destination} = {distance_km} km")
                        _distance_cache[cache_key] = distance_km
                        return distance_km
                    elif element.get("status") == "ZERO_RESULTS":
                        # No driving route (e.g., islands, different continents)
                        print(f"🚫 No driving route: {origin} → {destination}")
                        _distance_cache[cache_key] = None
                        return None
        
        except Exception as e:
            print(f"⚠️ Distance Matrix API failed: {e}")
    
    # Fallback: Calculate using Haversine if we have coordinates
    if origin_geo.get("lat") and dest_geo.get("lat"):
        distance = _haversine_distance(
            origin_geo["lat"], origin_geo["lng"],
            dest_geo["lat"], dest_geo["lng"]
        )
        print(f"📐 Haversine estimate: {origin} → {destination} = {distance} km")
        _distance_cache[cache_key] = distance
        return distance
    
    # Complete fallback
    print(f"⚠️ Cannot calculate distance: {origin} → {destination}")
    _distance_cache[cache_key] = None
    return None


async def is_driving_possible(origin: str, destination: str, google_key: Optional[str] = None) -> bool:
    """Check if driving is physically possible between two locations"""
    distance = await get_driving_distance(origin, destination, google_key)
    return distance is not None


def estimate_toll_cost(distance_km: int, origin_country: str, dest_country: str) -> int:
    """Estimate toll costs based on distance and countries traversed"""
    if not distance_km:
        return 0
    
    # Base toll rate per km by region
    TOLL_RATES = {
        "croatia": 0.08,    # HAC highways
        "slovenia": 0.05,   # Vignette system
        "austria": 0.06,    # Vignette + special tolls
        "italy": 0.10,      # Expensive tolls
        "france": 0.12,     # Very expensive
        "germany": 0.02,    # Mostly free
        "hungary": 0.04,    # Vignette
        "czech republic": 0.03,
        "slovakia": 0.03,
        "switzerland": 0.08,
        "spain": 0.09,
        "portugal": 0.08,
        "greece": 0.06,
        "united kingdom": 0.02,  # Few tolls
    }
    
    # Get average rate for route
    origin_rate = TOLL_RATES.get(origin_country, 0.05)
    dest_rate = TOLL_RATES.get(dest_country, 0.05)
    avg_rate = (origin_rate + dest_rate) / 2
    
    # Calculate toll
    toll = int(distance_km * avg_rate)
    
    # Add fixed costs (vignettes, tunnels)
    if origin_country in ["austria", "slovenia", "switzerland", "czech republic", "slovakia", "hungary"]:
        toll += 15  # Vignette
    if dest_country in ["austria", "slovenia", "switzerland", "czech republic", "slovakia", "hungary"]:
        toll += 15
    
    # Major tunnels
    if ("austria" in [origin_country, dest_country] or "switzerland" in [origin_country, dest_country]):
        if distance_km > 500:
            toll += 20  # Alpine tunnels
    
    return toll


def estimate_fuel_cost(distance_km: int) -> int:
    """Estimate fuel cost based on distance (assumes 7L/100km, €1.60/L)"""
    if not distance_km:
        return 0
    return int((distance_km / 100) * 7 * 1.60)


def estimate_driving_time(distance_km: int) -> str:
    """Estimate driving time (assumes 80km/h average including breaks)"""
    if not distance_km:
        return "?"
    
    hours = distance_km / 80
    
    if hours < 1:
        return f"{int(hours * 60)} min"
    elif hours < 10:
        return f"{int(hours)}h {int((hours % 1) * 60)}min"
    else:
        days = int(hours / 10)  # Max 10h driving per day
        return f"{int(hours)}h (preporučeno {days + 1} dana)"


async def build_smart_driving_option(origin: str, destination: str, google_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Build a complete driving option with accurate distance, cost, and time estimates.
    Works for ANY city pair in the world!
    """
    from urllib.parse import quote_plus
    
    key = google_key or os.getenv("GOOGLE_API_KEY")
    
    # Get distance
    distance_km = await get_driving_distance(origin, destination, key)
    
    if distance_km is None:
        return None  # Driving not possible
    
    # Get country info for toll calculation
    origin_geo = await geocode_city(origin, key)
    dest_geo = await geocode_city(destination, key)
    
    origin_country = origin_geo.get("country", "")
    dest_country = dest_geo.get("country", "")
    
    # Calculate costs
    fuel_cost = estimate_fuel_cost(distance_km)
    toll_cost = estimate_toll_cost(distance_km, origin_country, dest_country)
    total_cost = fuel_cost + toll_cost
    
    # Calculate time
    duration = estimate_driving_time(distance_km)
    
    # Google Maps link
    maps_link = f"https://www.google.com/maps/dir/{quote_plus(origin)}/{quote_plus(destination)}/"
    
    # Determine if multi-day recommended
    hours = distance_km / 80
    days_recommended = max(1, int(hours / 10) + 1)
    
    return {
        "mode": "car",
        "distance_km": distance_km,
        "duration": duration,
        "fuel_cost": fuel_cost,
        "toll_cost": toll_cost,
        "total_cost": total_cost,
        "days_recommended": days_recommended,
        "link": maps_link,
        "origin_country": origin_country,
        "destination_country": dest_country,
        "notes": _generate_route_notes(distance_km, origin_country, dest_country)
    }


def _generate_route_notes(distance_km: int, origin_country: str, dest_country: str) -> str:
    """Generate helpful notes about the route"""
    notes = []
    
    if distance_km < 100:
        notes.append("Kratka vožnja")
    elif distance_km < 300:
        notes.append("Ugodna dnevna vožnja")
    elif distance_km < 600:
        notes.append("Duža vožnja - preporučene pauze")
    elif distance_km < 1000:
        notes.append("Dugo putovanje - razmislite o noćenju usput")
    else:
        notes.append("Višednevno putovanje")
    
    # Country-specific notes
    if origin_country in ["austria", "slovenia", "switzerland"]:
        notes.append("Potrebna vinjeta!")
    if "italy" in [origin_country, dest_country]:
        notes.append("Skupe cestarine u Italiji")
    if "france" in [origin_country, dest_country]:
        notes.append("Skupe cestarine u Francuskoj")
    if "germany" in [origin_country, dest_country]:
        notes.append("Autoput uglavnom besplatan")
    
    return " | ".join(notes) if notes else "Ugodan put!"
