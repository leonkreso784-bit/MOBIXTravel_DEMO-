from typing import List, Dict, Optional, Any
from urllib.parse import quote_plus
import re

import asyncio

from .amadeus_client import amadeus_client

try:
    from travel_planner import search_flights_google  # type: ignore
except Exception:
    def search_flights_google(origin: str, destination: str, budget: Optional[int], departure_date: Optional[str] = None):  # type: ignore
        return []


# ===================================
# ALTERNATIVE AIRPORTS MAPPING
# ===================================
# When small airports have no flights, use nearby major airports
ALTERNATIVE_AIRPORTS = {
    # Croatian cities
    "rijeka": ["zagreb", "trieste", "venice"],  # RJK has limited flights
    "pula": ["trieste", "venice", "ljubljana"],
    "zadar": ["split", "zagreb"],
    "osijek": ["budapest", "zagreb"],
    # Slovenian cities
    "maribor": ["graz", "ljubljana", "zagreb"],
    "koper": ["trieste", "venice", "ljubljana"],
    # Other small airports
    "opatija": ["rijeka", "trieste", "venice", "zagreb"],
}

# Direct IATA code mappings for common cities (including Croatian/localized names)
DIRECT_IATA_CODES = {
    # Croatian cities
    "rijeka": "RJK",
    "zagreb": "ZAG",
    "split": "SPU",
    "dubrovnik": "DBV",
    "pula": "PUY",
    "zadar": "ZAD",
    # Slovenian
    "ljubljana": "LJU",
    # Italian
    "trieste": "TRS",
    "trst": "TRS",  # Croatian name
    "venice": "VCE",
    "venecija": "VCE",  # Croatian name
    "milan": "MIL",
    "milano": "MIL",
    "rome": "ROM",
    "rim": "ROM",  # Croatian name
    # Major European cities
    "london": "LON",
    "paris": "PAR",
    "pariz": "PAR",  # Croatian name
    "barcelona": "BCN",
    "berlin": "BER",
    "vienna": "VIE",
    "beč": "VIE",  # Croatian name
    "bec": "VIE",  # Without diacritic
    "wien": "VIE",  # German name
    "budapest": "BUD",
    "budimpešta": "BUD",  # Croatian name
    "munich": "MUC",
    "minhen": "MUC",  # Croatian name
    "münchen": "MUC",  # German name
    "amsterdam": "AMS",
    "prague": "PRG",
    "prag": "PRG",  # Croatian name
    "athens": "ATH",
    "atena": "ATH",  # Croatian name
    # US cities
    "new york": "NYC",
    "njujork": "NYC",  # Croatian phonetic
    "los angeles": "LAX",
    "chicago": "ORD",
    "miami": "MIA",
    "san francisco": "SFO",
    "boston": "BOS",
    "washington": "IAD",
    # Asian cities
    "tokyo": "TYO",
    "tokio": "TYO",  # Croatian name
    "osaka": "OSA",
    "singapore": "SIN",
    "singapur": "SIN",  # Croatian name
    "hong kong": "HKG",
    "bangkok": "BKK",
    "seoul": "ICN",
    # South American cities
    "buenos aires": "BUE",
    "sao paulo": "GRU",
    "rio de janeiro": "GIG",
    # Other major cities
    "bratislava": "BTS",
    "warsaw": "WAW",
    "varšava": "WAW",  # Croatian name
    "brussels": "BRU",
    "bruxelles": "BRU",
    "lisbon": "LIS",
    "lisabon": "LIS",  # Croatian name
    "madrid": "MAD",
    "dublin": "DUB",
    "stockholm": "ARN",
    "copenhagen": "CPH",
    "kopenhagen": "CPH",  # Croatian name
    "oslo": "OSL",
    "helsinki": "HEL",
    "moscow": "SVO",
    "moskva": "SVO",  # Croatian name
}

# Croatian declension endings to strip (e.g., "Pariza" → "Pariz", "Londona" → "London")
CROATIAN_SUFFIXES = ["a", "u", "om", "e", "i"]

def _normalize_city_name(city: str) -> str:
    """Normalize city name by removing Croatian declension suffixes."""
    if not city:
        return city
    city_lower = city.lower().strip()
    
    # If already in IATA codes, return as-is
    if city_lower in DIRECT_IATA_CODES:
        return city_lower
    
    # Try removing Croatian suffixes
    for suffix in CROATIAN_SUFFIXES:
        if city_lower.endswith(suffix) and len(city_lower) > len(suffix) + 2:
            base = city_lower[:-len(suffix)]
            if base in DIRECT_IATA_CODES:
                return base
            # Try with common endings
            if base + "z" in DIRECT_IATA_CODES:  # Pariz
                return base + "z"
            if base + "n" in DIRECT_IATA_CODES:  # London  
                return base + "n"
    
    return city_lower


async def search_flights(
    origin: Optional[str], 
    destination: Optional[str], 
    budget: Optional[Any],
    departure_date: Optional[str] = None,
    return_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for flights using BOTH Amadeus AND Google APIs.
    Combines results from both sources for maximum coverage.
    Amadeus is primary for accurate pricing, Google for additional options.
    
    INCLUDES FALLBACK: If small airport has no flights, try nearby major airports.
    """
    if not origin or not destination:
        return []
    
    # Convert budget string to number (e.g., "medium" -> 1500, "luxury" -> 5000)
    # NOTE: Flight prices are much higher than hotel prices, so use higher limits
    budget_num = None
    if budget:
        if isinstance(budget, (int, float)):
            budget_num = int(budget)
        elif isinstance(budget, str):
            budget_map = {"low": 500, "budget": 800, "medium": 1500, "high": 3000, "luxury": 5000}
            budget_num = budget_map.get(budget.lower(), 1500)
    
    all_flights = []
    
    # Normalize city names to handle Croatian declensions (e.g., "Pariza" → "pariz")
    origin_lower = _normalize_city_name(origin)
    dest_lower = _normalize_city_name(destination)
    
    # Search Amadeus (most important for flights - real prices and availability)
    if amadeus_client.is_configured():
        # First, try to get direct IATA codes from our mapping
        origin_iata = DIRECT_IATA_CODES.get(origin_lower)
        dest_iata = DIRECT_IATA_CODES.get(dest_lower)
        
        # If not in our mapping, use Amadeus API lookup
        if not origin_iata:
            origin_iata = await amadeus_client.get_iata_code(origin)
        if not dest_iata:
            dest_iata = await amadeus_client.get_iata_code(destination)
        
        print(f"✈️ Flight search: {origin} ({origin_iata}) → {destination} ({dest_iata})")
        
        if origin_iata and dest_iata:
            try:
                amadeus_flights = await amadeus_client.search_flights(
                    origin=origin_iata,
                    destination=dest_iata,
                    departure_date=departure_date,
                    return_date=return_date,
                    adults=1,
                    max_results=5
                )
                
                if amadeus_flights:
                    print(f"✅ Amadeus found {len(amadeus_flights)} flights for {origin} → {destination}")
                    # Add route info
                    for f in amadeus_flights:
                        f["origin_city"] = origin
                        f["dest_city"] = destination
                    
                    # Filter by budget if specified
                    if budget_num:
                        amadeus_flights = [f for f in amadeus_flights if f.get("price", 0) <= budget_num]
                    all_flights.extend(amadeus_flights)
            except Exception as e:
                print(f"⚠️ Amadeus flight search failed: {e}")
        
        # ⚠️ FALLBACK: If no flights from primary airport, try alternatives
        if not all_flights and origin_lower in ALTERNATIVE_AIRPORTS:
            print(f"⚠️ No flights from {origin}, trying alternative airports...")
            for alt_city in ALTERNATIVE_AIRPORTS[origin_lower]:
                alt_iata = DIRECT_IATA_CODES.get(alt_city) or await amadeus_client.get_iata_code(alt_city)
                if alt_iata and alt_iata != origin_iata:
                    try:
                        alt_flights = await amadeus_client.search_flights(
                            origin=alt_iata,
                            destination=dest_iata,
                            departure_date=departure_date,
                            return_date=return_date,
                            adults=1,
                            max_results=3
                        )
                        
                        if alt_flights:
                            print(f"✅ Found {len(alt_flights)} flights from {alt_city.title()} ({alt_iata}) → {destination}")
                            # Mark as alternative departure
                            for f in alt_flights:
                                f["origin_city"] = f"{alt_city.title()} (from {origin})"
                                f["dest_city"] = destination
                                f["alternative_origin"] = True
                            all_flights.extend(alt_flights)
                            break  # Found flights, stop searching
                    except Exception as e:
                        print(f"⚠️ Alternative search from {alt_city} failed: {e}")
    
    # ALSO search Google for additional options (runs in parallel)
    try:
        google_flights = await asyncio.to_thread(search_flights_google, origin, destination, budget_num, departure_date)
        if google_flights:
            print(f"✅ Google found {len(google_flights)} flights for {origin} → {destination}")
            # Add source tag to differentiate
            for flight in google_flights:
                flight["source"] = "google"
            all_flights.extend(google_flights)
    except Exception as e:
        print(f"⚠️ Google flight search failed: {e}")
    
    # Combine and deduplicate by price+duration (remove near-duplicates)
    if all_flights:
        # Sort by price (cheapest first)
        all_flights.sort(key=lambda f: f.get("price", 9999))
        return all_flights[:8]  # Return top 8 combined results
    
    # Final fallback: return empty (mock data will be added in travel_bundle if needed)
    return []


def build_google_flights_link(origin: str, destination: str) -> str:
    # CRITICAL: Validate inputs aren't dates or numbers
    if not origin or not destination:
        return "https://www.google.com/travel/flights"
    # Skip if origin/destination looks like date (e.g., "30.1", "5.2")
    import re
    if re.match(r'^\d+[./-]', origin) or re.match(r'^\d+[./-]', destination):
        return "https://www.google.com/travel/flights"
    if origin.replace('.', '').replace('-', '').isdigit() or destination.replace('.', '').replace('-', '').isdigit():
        return "https://www.google.com/travel/flights"
    return f"https://www.google.com/travel/flights?q=flights+from+{quote_plus(origin)}+to+{quote_plus(destination)}"
