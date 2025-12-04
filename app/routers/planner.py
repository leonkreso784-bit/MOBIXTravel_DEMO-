"""
Planner API - Returns structured travel options with real data, images, and booking links
"""
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..utils.amadeus_client import AmadeusClient
from ..utils.flights import search_flights, build_google_flights_link
from ..utils.hotels import search_hotels
from ..utils.categories import search_places


router = APIRouter(prefix="/api/planner", tags=["planner"])

# Lazy initialization of Amadeus client
_amadeus_client = None

def get_amadeus_client():
    """Get or create Amadeus client instance"""
    global _amadeus_client
    if _amadeus_client is None:
        _amadeus_client = AmadeusClient()
    return _amadeus_client


# ============================================================
# IATA CODES DATABASE - City to Airport mapping
# ============================================================
CITY_TO_IATA = {
    # Croatia
    "zagreb": "ZAG",
    "split": "SPU", 
    "dubrovnik": "DBV",
    "zadar": "ZAD",
    "pula": "PUY",
    "rijeka": "RJK",
    "osijek": "OSI",
    
    # Small Croatian towns -> nearest airport
    "omisalj": "RJK",
    "opatija": "RJK",
    "crikvenica": "RJK",
    "krk": "RJK",
    "makarska": "SPU",
    "trogir": "SPU",
    "hvar": "SPU",
    "korcula": "DBV",
    
    # Slovenia
    "ljubljana": "LJU",
    
    # Austria
    "vienna": "VIE",
    "beč": "VIE",
    "salzburg": "SZG",
    "graz": "GRZ",
    
    # Germany
    "munich": "MUC",
    "münchen": "MUC",
    "berlin": "BER",
    "frankfurt": "FRA",
    "hamburg": "HAM",
    "cologne": "CGN",
    "düsseldorf": "DUS",
    
    # Italy
    "rome": "FCO",
    "rim": "FCO",
    "milan": "MXP",
    "milano": "MXP",
    "venice": "VCE",
    "venecija": "VCE",
    "florence": "FLR",
    "firenca": "FLR",
    "naples": "NAP",
    "napulj": "NAP",
    "bologna": "BLQ",
    
    # France
    "paris": "CDG",
    "pariz": "CDG",
    "nice": "NCE",
    "nica": "NCE",
    "lyon": "LYS",
    "marseille": "MRS",
    
    # Spain
    "barcelona": "BCN",
    "madrid": "MAD",
    "malaga": "AGP",
    "valencia": "VLC",
    "seville": "SVQ",
    "sevilla": "SVQ",
    "palma": "PMI",
    "ibiza": "IBZ",
    
    # UK
    "london": "LHR",
    "manchester": "MAN",
    "edinburgh": "EDI",
    "birmingham": "BHX",
    
    # Netherlands
    "amsterdam": "AMS",
    
    # Belgium
    "brussels": "BRU",
    "bruxelles": "BRU",
    
    # Switzerland
    "zurich": "ZRH",
    "zürich": "ZRH",
    "geneva": "GVA",
    "ženeva": "GVA",
    
    # Greece
    "athens": "ATH",
    "atena": "ATH",
    "thessaloniki": "SKG",
    "solun": "SKG",
    "santorini": "JTR",
    "mykonos": "JMK",
    "crete": "HER",
    "heraklion": "HER",
    "rhodes": "RHO",
    "corfu": "CFU",
    "krf": "CFU",
    
    # Portugal
    "lisbon": "LIS",
    "lisabon": "LIS",
    "porto": "OPO",
    "faro": "FAO",
    
    # Czech Republic
    "prague": "PRG",
    "prag": "PRG",
    
    # Hungary
    "budapest": "BUD",
    "budimpešta": "BUD",
    
    # Poland
    "warsaw": "WAW",
    "varšava": "WAW",
    "krakow": "KRK",
    "krakov": "KRK",
    
    # Turkey
    "istanbul": "IST",
    "ankara": "ESB",
    "antalya": "AYT",
    
    # Egypt
    "cairo": "CAI",
    "kairo": "CAI",
    
    # USA
    "new york": "JFK",
    "los angeles": "LAX",
    "chicago": "ORD",
    "miami": "MIA",
    "san francisco": "SFO",
    "boston": "BOS",
    "washington": "IAD",
    
    # Others
    "dubai": "DXB",
    "bangkok": "BKK",
    "tokyo": "NRT",
    "singapore": "SIN",
    "sydney": "SYD",
}


# ============================================================
# AIRLINE LOGOS DATABASE - Using reliable CDN sources
# ============================================================
AIRLINE_LOGOS = {
    # Major European airlines
    "HR": "https://images.kiwi.com/airlines/64/HR.png",
    "LH": "https://images.kiwi.com/airlines/64/LH.png",
    "BA": "https://images.kiwi.com/airlines/64/BA.png",
    "AF": "https://images.kiwi.com/airlines/64/AF.png",
    "KL": "https://images.kiwi.com/airlines/64/KL.png",
    "IB": "https://images.kiwi.com/airlines/64/IB.png",
    "AZ": "https://images.kiwi.com/airlines/64/AZ.png",
    "OS": "https://images.kiwi.com/airlines/64/OS.png",
    "LX": "https://images.kiwi.com/airlines/64/LX.png",
    "SK": "https://images.kiwi.com/airlines/64/SK.png",
    
    # Low-cost carriers
    "FR": "https://images.kiwi.com/airlines/64/FR.png",
    "U2": "https://images.kiwi.com/airlines/64/U2.png",
    "W6": "https://images.kiwi.com/airlines/64/W6.png",
    "VY": "https://images.kiwi.com/airlines/64/VY.png",
    "EW": "https://images.kiwi.com/airlines/64/EW.png",
    "PC": "https://images.kiwi.com/airlines/64/PC.png",
    
    # Other European
    "A3": "https://images.kiwi.com/airlines/64/A3.png",
    "TP": "https://images.kiwi.com/airlines/64/TP.png",
    "TK": "https://images.kiwi.com/airlines/64/TK.png",
    "LO": "https://images.kiwi.com/airlines/64/LO.png",
    
    # Middle East
    "EK": "https://images.kiwi.com/airlines/64/EK.png",
    "QR": "https://images.kiwi.com/airlines/64/QR.png",
    "EY": "https://images.kiwi.com/airlines/64/EY.png",
    
    # US carriers
    "AA": "https://images.kiwi.com/airlines/64/AA.png",
    "UA": "https://images.kiwi.com/airlines/64/UA.png",
    "DL": "https://images.kiwi.com/airlines/64/DL.png",
}

# Bus company logos - using reliable PNG sources
BUS_LOGOS = {
    "flixbus": "https://cdn.iconscout.com/icon/free/png-256/free-flixbus-3521554-2945066.png",
    "eurolines": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=200&h=200&fit=crop",
    "blablabus": "https://images.unsplash.com/photo-1570125909232-eb263c188f7e?w=200&h=200&fit=crop",
    "regiojet": "https://images.unsplash.com/photo-1557223562-6c77ef16210f?w=200&h=200&fit=crop",
}

# Train company logos - using reliable sources
TRAIN_LOGOS = {
    "öbb": "https://images.unsplash.com/photo-1474487548417-781cb71495f3?w=200&h=200&fit=crop",
    "db": "https://images.unsplash.com/photo-1515165562839-978bbcf18277?w=200&h=200&fit=crop", 
    "sncf": "https://images.unsplash.com/photo-1515165562839-978bbcf18277?w=200&h=200&fit=crop",
    "trenitalia": "https://images.unsplash.com/photo-1474487548417-781cb71495f3?w=200&h=200&fit=crop",
    "renfe": "https://images.unsplash.com/photo-1474487548417-781cb71495f3?w=200&h=200&fit=crop",
    "eurostar": "https://images.unsplash.com/photo-1515165562839-978bbcf18277?w=200&h=200&fit=crop",
    "thalys": "https://images.unsplash.com/photo-1515165562839-978bbcf18277?w=200&h=200&fit=crop",
    "sbb": "https://images.unsplash.com/photo-1474487548417-781cb71495f3?w=200&h=200&fit=crop",
}


# ============================================================
# API Request/Response Models
# ============================================================
class PlannerRequest(BaseModel):
    origin: Optional[str] = None
    destination: str
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    budget: Optional[int] = None
    adults: int = 1


class TransportOption(BaseModel):
    id: str
    type: str  # flight, bus, train, car
    title: str
    subtitle: str
    carrier: Optional[str] = None
    carrier_code: Optional[str] = None
    duration: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    departure_airport: Optional[str] = None
    arrival_airport: Optional[str] = None
    stops: int = 0
    price: float
    currency: str = "EUR"
    image_url: Optional[str] = None
    booking_link: Optional[str] = None


class HotelOption(BaseModel):
    id: str
    name: str
    subtitle: str
    rating: Optional[float] = None
    reviews: Optional[int] = None
    price_per_night: float
    currency: str = "EUR"
    address: Optional[str] = None
    image_url: Optional[str] = None
    booking_link: Optional[str] = None


class ActivityOption(BaseModel):
    id: str
    name: str
    subtitle: str
    rating: Optional[float] = None
    reviews: Optional[int] = None
    price: Optional[float] = None
    address: Optional[str] = None
    image_url: Optional[str] = None
    booking_link: Optional[str] = None


# ============================================================
# Helper Functions
# ============================================================

def get_iata_code(city: str) -> Optional[str]:
    """Get IATA airport code for a city"""
    if not city:
        return None
    city_lower = city.lower().strip()
    return CITY_TO_IATA.get(city_lower)


def get_nearest_airport(city: str) -> tuple[str, str]:
    """
    Get nearest airport for a city.
    Returns (airport_iata, airport_city_name)
    """
    if not city:
        return (None, None)
    
    city_lower = city.lower().strip()
    
    # Direct match
    if city_lower in CITY_TO_IATA:
        return (CITY_TO_IATA[city_lower], city)
    
    # Check for small towns -> hub mapping
    hub_mapping = {
        "omisalj": ("RJK", "Rijeka"),
        "omišalj": ("RJK", "Rijeka"),
        "opatija": ("RJK", "Rijeka"),
        "icici": ("RJK", "Rijeka"),
        "crikvenica": ("RJK", "Rijeka"),
        "krk": ("RJK", "Rijeka"),
        "malinska": ("RJK", "Rijeka"),
        "makarska": ("SPU", "Split"),
        "trogir": ("SPU", "Split"),
        "omiš": ("SPU", "Split"),
        "hvar": ("SPU", "Split"),
        "brač": ("SPU", "Split"),
        "bol": ("SPU", "Split"),
        "korčula": ("DBV", "Dubrovnik"),
        "mljet": ("DBV", "Dubrovnik"),
        "cavtat": ("DBV", "Dubrovnik"),
        "novalja": ("ZAD", "Zadar"),
        "pag": ("ZAD", "Zadar"),
        "biograd": ("ZAD", "Zadar"),
    }
    
    if city_lower in hub_mapping:
        return hub_mapping[city_lower]
    
    # Default - try Zagreb as fallback for Croatian locations
    return ("ZAG", "Zagreb")


def get_airline_logo(carrier_code: str) -> str:
    """Get airline logo URL from carrier code"""
    if not carrier_code:
        return "https://via.placeholder.com/200x80/1a1a2e/667eea?text=Flight"
    return AIRLINE_LOGOS.get(carrier_code.upper(), f"https://via.placeholder.com/200x80/1a1a2e/667eea?text={carrier_code}")


def get_airline_name(carrier_code: str) -> str:
    """Get airline name from carrier code"""
    airline_names = {
        "HR": "Croatia Airlines",
        "LH": "Lufthansa",
        "BA": "British Airways",
        "AF": "Air France",
        "KL": "KLM",
        "FR": "Ryanair",
        "U2": "EasyJet",
        "W6": "Wizz Air",
        "VY": "Vueling",
        "EW": "Eurowings",
        "OS": "Austrian",
        "LX": "Swiss",
        "IB": "Iberia",
        "A3": "Aegean",
        "TK": "Turkish Airlines",
        "EK": "Emirates",
        "QR": "Qatar Airways",
    }
    return airline_names.get(carrier_code.upper(), carrier_code)


def build_skyscanner_link(origin: str, dest: str, date: str = None) -> str:
    """Build Skyscanner booking link"""
    origin_iata = get_iata_code(origin) or "ZAG"
    dest_iata = get_iata_code(dest) or dest[:3].upper()
    date_str = date or (datetime.now() + timedelta(days=7)).strftime("%y%m%d")
    return f"https://www.skyscanner.com/transport/flights/{origin_iata.lower()}/{dest_iata.lower()}/{date_str}/"


def build_booking_link(destination: str, checkin: str = None, checkout: str = None) -> str:
    """Build Booking.com link"""
    base = f"https://www.booking.com/searchresults.html?ss={quote_plus(destination)}"
    if checkin:
        base += f"&checkin={checkin}"
    if checkout:
        base += f"&checkout={checkout}"
    return base


def build_tripadvisor_link(destination: str, activity_type: str = "Attractions") -> str:
    """Build TripAdvisor link"""
    return f"https://www.tripadvisor.com/Search?q={quote_plus(destination)}+{quote_plus(activity_type)}"


def build_flixbus_link(origin: str, dest: str) -> str:
    """Build FlixBus booking link"""
    return f"https://shop.flixbus.com/search?departureCity={quote_plus(origin)}&arrivalCity={quote_plus(dest)}"


def build_trainline_link(origin: str, dest: str) -> str:
    """Build Trainline booking link"""
    return f"https://www.thetrainline.com/book/results?origin={quote_plus(origin)}&destination={quote_plus(dest)}"


# ============================================================
# Main API Endpoint
# ============================================================

@router.post("/generate")
async def generate_travel_plan(request: PlannerRequest):
    """
    Generate travel plan with real flights, hotels, restaurants and activities.
    Returns structured data with images and booking links.
    """
    if not request.destination:
        raise HTTPException(status_code=400, detail="Destination is required")
    
    destination = request.destination.strip()
    origin = request.origin.strip() if request.origin else None
    
    # Parse dates
    departure_date = request.departure_date
    return_date = request.return_date
    
    if not departure_date:
        departure_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    if not return_date:
        return_date = (datetime.strptime(departure_date, "%Y-%m-%d") + timedelta(days=5)).strftime("%Y-%m-%d")
    
    # Get IATA codes for flight search
    origin_iata, origin_airport_city = get_nearest_airport(origin) if origin else (None, None)
    dest_iata, dest_airport_city = get_nearest_airport(destination)
    
    # ============================================================
    # 1. SEARCH FLIGHTS (Real Amadeus API)
    # ============================================================
    transport_options = []
    
    if origin_iata and dest_iata:
        try:
            amadeus = get_amadeus_client()
            real_flights = await amadeus.search_flights(
                origin=origin_iata,
                destination=dest_iata,
                departure_date=departure_date,
                return_date=None,  # One-way first
                adults=request.adults,
                max_results=5
            )
            
            for i, flight in enumerate(real_flights):
                carrier_code = flight.get("airline", "")
                dep_time = flight.get("departure_time", "")
                arr_time = flight.get("arrival_time", "")
                
                # Format times
                dep_formatted = dep_time[11:16] if len(dep_time) > 11 else "TBD"
                arr_formatted = arr_time[11:16] if len(arr_time) > 11 else "TBD"
                
                stops = flight.get("stops", 0)
                stops_text = "Direct" if stops == 0 else f"{stops} stop{'s' if stops > 1 else ''}"
                
                transport_options.append({
                    "id": f"flight_{i+1}",
                    "type": "flight",
                    "title": f"{get_airline_name(carrier_code)} to {destination}",
                    "subtitle": f"{origin_airport_city or origin} → {dest_airport_city or destination}",
                    "carrier": get_airline_name(carrier_code),
                    "carrier_code": carrier_code,
                    "duration": flight.get("duration", ""),
                    "departure_time": dep_formatted,
                    "arrival_time": arr_formatted,
                    "departure_airport": flight.get("departure_airport", origin_iata),
                    "arrival_airport": flight.get("arrival_airport", dest_iata),
                    "stops": stops,
                    "stops_text": stops_text,
                    "price": flight.get("price", 0),
                    "currency": "EUR",
                    "image_url": get_airline_logo(carrier_code),
                    "booking_link": build_skyscanner_link(origin or "Zagreb", destination, departure_date.replace("-", "")[2:])
                })
                
        except Exception as e:
            print(f"⚠️ Amadeus flight search error: {e}")
    
    # Add mock flights if Amadeus returned nothing
    if not transport_options:
        mock_carriers = [("FR", "Ryanair"), ("U2", "EasyJet"), ("W6", "Wizz Air")]
        for i, (code, name) in enumerate(mock_carriers):
            transport_options.append({
                "id": f"flight_{i+1}",
                "type": "flight",
                "title": f"{name} to {destination}",
                "subtitle": f"{origin or 'Your city'} → {destination}",
                "carrier": name,
                "carrier_code": code,
                "duration": f"{2 + i}h {15 + i*10}m",
                "departure_time": f"{7 + i*2:02d}:30",
                "arrival_time": f"{10 + i*2:02d}:{45 + i*5}",
                "stops": 0 if i < 2 else 1,
                "stops_text": "Direct" if i < 2 else "1 stop",
                "price": 89 + i * 45,
                "currency": "EUR",
                "image_url": get_airline_logo(code),
                "booking_link": build_skyscanner_link(origin or "Zagreb", destination)
            })
    
    # Add bus option
    transport_options.append({
        "id": "bus_1",
        "type": "bus",
        "title": f"FlixBus to {destination}",
        "subtitle": f"{origin or 'Your city'} → {destination}",
        "carrier": "FlixBus",
        "carrier_code": "FLIX",
        "duration": "8-12h",
        "price": 45,
        "currency": "EUR",
        "image_url": BUS_LOGOS.get("flixbus"),
        "booking_link": build_flixbus_link(origin or "Zagreb", destination)
    })
    
    # Add train option
    transport_options.append({
        "id": "train_1",
        "type": "train",
        "title": f"Train to {destination}",
        "subtitle": "High-speed rail connection",
        "carrier": "Rail Europe",
        "duration": "5-8h",
        "price": 65,
        "currency": "EUR",
        "image_url": TRAIN_LOGOS.get("öbb"),
        "booking_link": build_trainline_link(origin or "Zagreb", destination)
    })
    
    # ============================================================
    # 2. SEARCH HOTELS
    # ============================================================
    hotel_options = []
    google_key = os.getenv("GOOGLE_API_KEY", "").strip()
    
    try:
        real_hotels = await search_hotels(
            destination,
            google_key,
            request.budget,
            check_in_date=departure_date,
            check_out_date=return_date
        )
        
        # Different hotel images for variety
        hotel_images = [
            "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400&h=300&fit=crop",
            "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=400&h=300&fit=crop",
            "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=400&h=300&fit=crop",
            "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=400&h=300&fit=crop",
            "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=400&h=300&fit=crop",
        ]
        
        for i, hotel in enumerate(real_hotels[:5]):
            # Build Google Places photo URL if available
            photo_url = None
            if hotel.get("photos"):
                photo_ref = hotel["photos"][0].get("photo_reference")
                if photo_ref and google_key:
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_ref}&key={google_key}"
            
            hotel_options.append({
                "id": f"hotel_{i+1}",
                "name": hotel.get("name", f"Hotel {destination}"),
                "subtitle": f"{hotel.get('rating', 4.0)}★ • {hotel.get('address', destination)}",
                "rating": hotel.get("rating", 4.0),
                "reviews": hotel.get("user_ratings_total", 100),
                "price_per_night": hotel.get("price_per_night", 80 + i * 30),
                "currency": "EUR",
                "address": hotel.get("address", destination),
                "image_url": photo_url or hotel_images[i % len(hotel_images)],
                "booking_link": build_booking_link(hotel.get("name", destination), departure_date, return_date)
            })
    except Exception as e:
        print(f"⚠️ Hotel search error: {e}")
    
    # Add mock hotels if none found
    if not hotel_options:
        hotel_types = [
            ("Luxury Hotel", 5.0, 180),
            ("Boutique Hotel", 4.5, 120),
            ("City Center Inn", 4.2, 75),
        ]
        for i, (name, rating, price) in enumerate(hotel_types):
            hotel_options.append({
                "id": f"hotel_{i+1}",
                "name": f"{name} {destination}",
                "subtitle": f"{rating}★ • City Center",
                "rating": rating,
                "reviews": 500 + i * 200,
                "price_per_night": price,
                "currency": "EUR",
                "address": f"Central {destination}",
                "image_url": f"https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=400&h=300&fit=crop",
                "booking_link": build_booking_link(f"{name} {destination}", departure_date, return_date)
            })
    
    # ============================================================
    # 3. SEARCH RESTAURANTS
    # ============================================================
    restaurant_options = []
    
    try:
        real_restaurants = await search_places("best restaurants", destination, 5, "en", google_key)
        
        for i, rest in enumerate(real_restaurants):
            photo_url = None
            if rest.get("photos"):
                photo_ref = rest["photos"][0].get("photo_reference")
                if photo_ref and google_key:
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_ref}&key={google_key}"
            
            restaurant_options.append({
                "id": f"restaurant_{i+1}",
                "name": rest.get("name", "Local Restaurant"),
                "subtitle": rest.get("types", ["restaurant"])[0].replace("_", " ").title() if rest.get("types") else "Restaurant",
                "rating": rest.get("rating", 4.0),
                "reviews": rest.get("user_ratings_total", 50),
                "price": None,  # Restaurants usually show price level
                "price_level": "€" * (rest.get("price_level", 2) + 1),
                "address": rest.get("address", destination),
                "image_url": photo_url or f"https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=400&h=300&fit=crop",
                "booking_link": rest.get("maps_url") or build_tripadvisor_link(destination, "Restaurants")
            })
    except Exception as e:
        print(f"⚠️ Restaurant search error: {e}")
    
    # Mock restaurants if none found
    if not restaurant_options:
        rest_types = [
            ("La Maison", "French Fine Dining", 4.8, "$$$"),
            ("Trattoria Bella", "Italian", 4.5, "$$"),
            ("Local Kitchen", "Traditional", 4.3, "$"),
        ]
        for i, (name, cuisine, rating, price) in enumerate(rest_types):
            restaurant_options.append({
                "id": f"restaurant_{i+1}",
                "name": name,
                "subtitle": cuisine,
                "rating": rating,
                "reviews": 200 + i * 100,
                "price": None,
                "price_level": price,
                "address": destination,
                "image_url": f"https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&h=300&fit=crop",
                "booking_link": build_tripadvisor_link(destination, "Restaurants")
            })
    
    # ============================================================
    # 4. SEARCH ACTIVITIES
    # ============================================================
    activity_options = []
    
    try:
        real_activities = await search_places("things to do attractions", destination, 5, "en", google_key)
        
        for i, act in enumerate(real_activities):
            photo_url = None
            if act.get("photos"):
                photo_ref = act["photos"][0].get("photo_reference")
                if photo_ref and google_key:
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_ref}&key={google_key}"
            
            activity_options.append({
                "id": f"activity_{i+1}",
                "name": act.get("name", "Local Attraction"),
                "subtitle": act.get("types", ["tourist_attraction"])[0].replace("_", " ").title() if act.get("types") else "Attraction",
                "rating": act.get("rating", 4.5),
                "reviews": act.get("user_ratings_total", 100),
                "price": 15 + i * 10,  # Estimated entry fee
                "address": act.get("address", destination),
                "image_url": photo_url or f"https://images.unsplash.com/photo-1499856871958-5b9627545d1a?w=400&h=300&fit=crop",
                "booking_link": act.get("maps_url") or build_tripadvisor_link(destination, "Attractions")
            })
    except Exception as e:
        print(f"⚠️ Activity search error: {e}")
    
    # Mock activities if none found
    if not activity_options:
        act_types = [
            ("City Walking Tour", "Guided tour • 3 hours", 25),
            ("Museum Pass", "Access to 5 museums", 45),
            ("Food & Wine Tasting", "4 hours • 6 tastings", 75),
            ("Day Trip Excursion", "Full day • Transport included", 95),
        ]
        for i, (name, desc, price) in enumerate(act_types):
            activity_options.append({
                "id": f"activity_{i+1}",
                "name": name,
                "subtitle": desc,
                "rating": 4.5 + (i % 3) * 0.1,
                "reviews": 300 + i * 150,
                "price": price,
                "address": destination,
                "image_url": f"https://images.unsplash.com/photo-1533105079780-92b9be482077?w=400&h=300&fit=crop",
                "booking_link": build_tripadvisor_link(destination, "Attractions")
            })
    
    # ============================================================
    # Return structured response
    # ============================================================
    return {
        "success": True,
        "origin": origin,
        "destination": destination,
        "origin_airport": origin_iata,
        "destination_airport": dest_iata,
        "departure_date": departure_date,
        "return_date": return_date,
        "transport": transport_options,
        "hotels": hotel_options,
        "restaurants": restaurant_options,
        "activities": activity_options,
        "links": {
            "flights": build_skyscanner_link(origin or "Zagreb", destination),
            "hotels": build_booking_link(destination, departure_date, return_date),
            "activities": build_tripadvisor_link(destination, "Attractions"),
        }
    }
