import os
import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote_plus

import httpx

CATEGORY_CONFIG = {
    "restaurants": {
        "keywords": ["restaurant", "restoran", "eat", "dining", "food", "bistro", "jesti", "hrana", "ručak", "večera"],
        "query": "best restaurants",
        "label": "restaurants",
        "card_type": "restaurant",
    },
    "pizzerias": {
        "keywords": ["pizza", "pizzer", "pizzeria", "pizzerija"],
        "query": "best pizza restaurants",
        "label": "pizzerias",
        "card_type": "restaurant",
    },
    "bakeries": {
        "keywords": ["slastičar", "slasticar", "bakery", "pastry", "kolač", "kolac", "torta", "sladoled", "slastice", "dessert", "sweets", "cake", "cakes", "pastries"],
        "query": "slastičarna pastry shop cake",
        "label": "bakeries & pastry shops",
        "card_type": "restaurant",
    },
    "nightlife": {
        "keywords": ["club", "nightclub", "bar", "nightlife", "party", "noćni", "nocni", "klub", "zabava", "izlazak", "clubbing"],
        "query": "best nightlife",
        "label": "nightlife spots",
        "card_type": "activity",
    },
    "cafes": {
        "keywords": ["cafe", "coffee", "kafić", "kafic", "espresso", "kava", "kavana"],
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
        "keywords": ["things to do", "što raditi", "activities", "attractions", "poi", "zanimljivosti", "sights", "znamenitost"],
        "query": "things to do",
        "label": "activities",
        "card_type": "activity",
    },
}

# Croatian city names for detection
CROATIAN_CITIES = [
    "zagreb", "split", "rijeka", "osijek", "zadar", "pula", "slavonski brod", "karlovac",
    "varaždin", "šibenik", "sisak", "vinkovci", "dubrovnik", "bjelovar", "koprivnica",
    "opatija", "rovinj", "poreč", "porec", "umag", "mali lošinj", "crikvenica", "senj",
    "makarska", "trogir", "omiš", "omis", "hvar", "korčula", "korcula", "vis", "bol", "brač", "brac",
    "ogulin", "samobor", "velika gorica", "požega", "vukovar", "virovitica", "čakovec",
    "gospić", "knin", "sinj", "solin", "metković", "ploče", "novalja", "biograd", "nin",
    "krk", "cres", "rab", "pag", "lošinj", "losinj", "murter", "primošten", "vodice",
    "ičići", "lovran", "mošćenička draga", "kastav", "klana", "matulji", "opatija", "volosko",
    # Otoci/mjesta
    "omišalj", "malinska", "njivice", "baška", "vrbnik", "punat", "kornić", "dobrinj",
]

# International cities for Google Places search
INTERNATIONAL_CITIES = [
    # Europe
    "paris", "london", "rome", "roma", "berlin", "madrid", "barcelona", "amsterdam",
    "prague", "vienna", "wien", "budapest", "lisbon", "lisboa", "athens", "atena",
    "munich", "münchen", "milan", "milano", "venice", "venezia", "florence", "firenze",
    "brussels", "bruxelles", "zurich", "zürich", "geneva", "stockholm", "oslo", "copenhagen",
    "dublin", "edinburgh", "manchester", "liverpool", "nice", "marseille", "lyon",
    "monaco", "santorini", "mykonos", "crete", "rhodes", "corfu", "porto", "seville",
    "valencia", "malaga", "ibiza", "mallorca", "palma", "cannes", "monte carlo",
    # Balkans
    "belgrade", "beograd", "sarajevo", "ljubljana", "skopje", "podgorica", "tirana",
    "sofia", "bucharest", "bucuresti", "thessaloniki", "solun",
    # Americas
    "new york", "los angeles", "miami", "chicago", "san francisco", "las vegas",
    "boston", "washington", "seattle", "toronto", "vancouver", "montreal",
    "mexico city", "cancun", "rio de janeiro", "sao paulo", "buenos aires",
    # Asia & Middle East
    "tokyo", "kyoto", "osaka", "seoul", "beijing", "shanghai", "hong kong",
    "singapore", "bangkok", "bali", "phuket", "dubai", "abu dhabi", "istanbul",
    "tel aviv", "jerusalem", "mumbai", "delhi", "goa",
    # Oceania & Africa
    "sydney", "melbourne", "auckland", "cape town", "marrakech", "cairo",
]

# Combined list for all city searches
ALL_CITIES = CROATIAN_CITIES + INTERNATIONAL_CITIES

# Patterns to detect location queries in messages
LOCATION_QUERY_PATTERNS = [
    # Croatian patterns
    r"(?:najbolj[aei]|dobr[aei]|preporuč[ui]|tražim|gdje|koji|kakvi|ima li)\s+(?:\w+\s+)?(?:\w+\s+)?(?:u|na)\s+([A-ZČĆŠĐŽa-zčćšđž\s]+?)(?:\?|$|,|\.|!)",
    r"(?:u|na)\s+([A-ZČĆŠĐŽa-zčćšđž\s]+?)\s+(?:najbolj|dobr|preporuč|ima li|koji|kakvi)",
    r"([A-ZČĆŠĐŽa-zčćšđž]+)\s+(?:restorani|kafići|slastičarnice|pizzerije|hoteli|barovi)",
    # English patterns  
    r"(?:best|good|recommend|find|where)\s+(?:\w+\s+)?(?:\w+\s+)?(?:in|at|near)\s+([A-Za-z\s]+?)(?:\?|$|,|\.|!)",
    r"(?:in|at|near)\s+([A-Za-z\s]+?)\s+(?:restaurants?|cafes?|hotels?|bars?|clubs?)",
    # German patterns
    r"(?:beste|gute|empfehlen)\s+(?:\w+\s+)?(?:\w+\s+)?(?:in|bei)\s+([A-Za-zäöüÄÖÜß\s]+?)(?:\?|$|,|\.|!)",
]

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
    "pizzerias": [
        {"name": "Pizza Roma {city}", "address": "Main street, {city}", "rating": 4.7},
        {"name": "Napoli Express", "address": "City center, {city}", "rating": 4.6},
        {"name": "La Pizzeria", "address": "Old town, {city}", "rating": 4.5},
    ],
    "bakeries": [
        {"name": "Dolce Vita {city}", "address": "Main square, {city}", "rating": 4.8},
        {"name": "Sweet Dreams Bakery", "address": "City center, {city}", "rating": 4.6},
        {"name": "Pasticceria Milano", "address": "Waterfront, {city}", "rating": 4.7},
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


def is_location_query(message: str) -> bool:
    """Check if the message is asking about places/locations."""
    msg = (message or "").lower()
    
    # Check for place-related keywords
    place_keywords = [
        "restoran", "restaurant", "kafić", "cafe", "coffee", "slastičar", "bakery", 
        "pizza", "hotel", "bar", "club", "klub", "night", "noć", "znamenitost",
        "attraction", "beach", "plaž", "museum", "muzej", "park", "najbolji", "best",
        "preporuči", "recommend", "tražim", "find", "gdje", "where", "koji", "which"
    ]
    
    has_place_keyword = any(kw in msg for kw in place_keywords)
    
    # Check for city names (both Croatian and international)
    has_city = any(city.lower() in msg for city in ALL_CITIES)
    
    # Also check for location prepositions with question words
    location_phrases = [
        r"u\s+[A-ZČĆŠĐŽa-zčćšđž]+", r"in\s+[A-Za-z]+", r"na\s+[A-ZČĆŠĐŽa-zčćšđž]+",
        r"restorani\b", r"kafići\b", r"slastičarnice\b", r"pizzerije\b", r"hoteli\b"
    ]
    has_location_phrase = any(re.search(pat, msg, re.IGNORECASE) for pat in location_phrases)
    
    return has_place_keyword and (has_city or has_location_phrase)


def extract_city_from_message(message: str) -> Optional[str]:
    """Extract city name from user message."""
    msg = (message or "").lower()
    
    # Normalization map for Croatian declensions (lokativ -> nominativ)
    CITY_NORMALIZATION = {
        "opatiji": "opatija", "zagrebu": "zagreb", "rijeci": "rijeka", "splitu": "split",
        "dubrovniku": "dubrovnik", "puli": "pula", "zadru": "zadar", "šibeniku": "šibenik",
        "osijeku": "osijek", "karlovcu": "karlovac", "varaždinu": "varaždin", "rovinju": "rovinj",
        "poreču": "poreč", "makarskoj": "makarska", "trogiru": "trogir", "hvaru": "hvar",
        "korčuli": "korčula", "krku": "krk", "rabu": "rab", "pagu": "pag", "cresu": "cres",
        "lovranu": "lovran", "mošćeničkoj dragi": "mošćenička draga", "medulinu": "medulin",
        "omišlju": "omišalj", "malinski": "malinska", "baškoj": "baška", "vodicama": "vodice",
        "novalji": "novalja", "biogradu": "biograd", "ninu": "nin", "solinu": "solin",
        "sinju": "sinj", "vukovaru": "vukovar", "vinkovcima": "vinkovci", "kninu": "knin",
    }
    
    # FIRST: Check for declensions (more specific matches first)
    for declension, nominativ in CITY_NORMALIZATION.items():
        if declension in msg:
            return nominativ.title()
    
    # SECOND: Try to find a known city (exact word boundary match)
    # Sort cities by length (longest first) to avoid partial matches like "bol" in "najbolje"
    sorted_cities = sorted(ALL_CITIES, key=len, reverse=True)
    for city in sorted_cities:
        # Use word boundary check to avoid matching "bol" in "najbolje"
        pattern = r'\b' + re.escape(city.lower()) + r'\b'
        if re.search(pattern, msg):
            return city.title()
    
    # Try regex patterns
    for pattern in LOCATION_QUERY_PATTERNS:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            potential_city = match.group(1).strip()
            # Clean up the city name
            potential_city = re.sub(r"[^\w\s]", "", potential_city).strip().lower()
            
            # Check if it's a known declension
            if potential_city in CITY_NORMALIZATION:
                return CITY_NORMALIZATION[potential_city].title()
            
            if potential_city and len(potential_city) > 2:
                return potential_city.title()
    
    return None


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
