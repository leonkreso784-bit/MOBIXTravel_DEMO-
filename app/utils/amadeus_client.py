"""
Amadeus API Client for flight and hotel search.
Provides OAuth token management and search endpoints with fallback support.
"""
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx


class AmadeusClient:
    """
    Client for Amadeus Travel APIs (test and production environments).
    Handles OAuth token management and flight/hotel searches.
    """
    
    def __init__(self):
        self.client_id = os.getenv("AMADEUS_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("AMADEUS_CLIENT_SECRET", "").strip()
        self.env = os.getenv("AMADEUS_ENV", "test").strip().lower()
        
        # Base URLs
        if self.env == "production":
            self.base_url = "https://api.amadeus.com"
        else:
            self.base_url = "https://test.api.amadeus.com"
        
        # Token cache
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    def is_configured(self) -> bool:
        """Check if Amadeus credentials are configured."""
        return bool(self.client_id and self.client_secret)
    
    async def _get_access_token(self) -> Optional[str]:
        """
        Get OAuth access token from Amadeus.
        Caches token and reuses until expiration.
        """
        # Return cached token if still valid
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._access_token
        
        if not self.is_configured():
            return None
        
        # Request new token
        url = f"{self.base_url}/v1/security/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, headers=headers, data=data)
                
                if response.status_code != 200:
                    print(f"⚠️ Amadeus token request failed: {response.status_code}")
                    return None
                
                token_data = response.json()
                self._access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 1800)  # Default 30 min
                
                # Cache token with 5-minute safety margin
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
                
                return self._access_token
        
        except Exception as e:
            print(f"⚠️ Amadeus token error: {e}")
            return None
    
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: Optional[str] = None,
        return_date: Optional[str] = None,
        adults: int = 1,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for flight offers using Amadeus Flight Offers Search API.
        
        Args:
            origin: IATA airport code (e.g., "ZAG" for Zagreb)
            destination: IATA airport code (e.g., "ATH" for Athens)
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format (optional for one-way)
            adults: Number of adult passengers (default 1)
            max_results: Maximum number of results to return (default 5)
        
        Returns:
            List of flight offers with price, duration, airline info
        """
        if not self.is_configured():
            return []
        
        token = await self._get_access_token()
        if not token:
            return []
        
        # Default to 7 days from now if no date provided
        if not departure_date:
            dep_date = datetime.now() + timedelta(days=7)
            departure_date = dep_date.strftime("%Y-%m-%d")
        
        # Build API request
        url = f"{self.base_url}/v2/shopping/flight-offers"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "originLocationCode": origin.upper()[:3],
            "destinationLocationCode": destination.upper()[:3],
            "departureDate": departure_date,
            "adults": adults,
            "max": max_results,
            "currencyCode": "EUR",
        }
        
        # Add return date if provided (round-trip)
        if return_date:
            params["returnDate"] = return_date
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    print(f"⚠️ Amadeus flight search failed: {response.status_code}")
                    return []
                
                data = response.json()
                flights = []
                
                for offer in data.get("data", [])[:max_results]:
                    # Extract first itinerary (outbound)
                    itinerary = offer.get("itineraries", [{}])[0]
                    segments = itinerary.get("segments", [])
                    
                    if not segments:
                        continue
                    
                    first_segment = segments[0]
                    last_segment = segments[-1]
                    
                    # Calculate total duration
                    duration_iso = itinerary.get("duration", "PT0H")
                    duration_text = self._format_duration(duration_iso)
                    
                    # Extract pricing
                    price = offer.get("price", {})
                    total_price = float(price.get("total", 0))
                    
                    # Extract airline info
                    carrier_code = first_segment.get("carrierCode", "??")
                    
                    # Number of stops
                    stops = len(segments) - 1
                    
                    flights.append({
                        "airline": carrier_code,
                        "price": int(total_price),
                        "currency": "EUR",
                        "duration": duration_text,
                        "stops": stops,
                        "departure_time": first_segment.get("departure", {}).get("at", ""),
                        "arrival_time": last_segment.get("arrival", {}).get("at", ""),
                        "departure_airport": first_segment.get("departure", {}).get("iataCode", ""),
                        "arrival_airport": last_segment.get("arrival", {}).get("iataCode", ""),
                        "source": "amadeus",
                    })
                
                return flights
        
        except Exception as e:
            print(f"⚠️ Amadeus flight search error: {e}")
            return []
    
    async def search_hotels(
        self,
        city_code: str,
        check_in_date: Optional[str] = None,
        check_out_date: Optional[str] = None,
        adults: int = 1,
        max_price: Optional[int] = None,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for hotel offers using Amadeus Hotel Search API.
        
        Args:
            city_code: IATA city code (e.g., "ATH" for Athens, "ZAG" for Zagreb)
            check_in_date: Check-in date in YYYY-MM-DD format
            check_out_date: Check-out date in YYYY-MM-DD format
            adults: Number of adults (default 1)
            max_price: Maximum price per night in EUR (optional)
            max_results: Maximum number of results to return (default 5)
        
        Returns:
            List of hotel offers with name, rating, price info
        """
        if not self.is_configured():
            return []
        
        token = await self._get_access_token()
        if not token:
            return []
        
        # Default to 7 days from now if no dates provided
        if not check_in_date:
            check_in = datetime.now() + timedelta(days=7)
            check_in_date = check_in.strftime("%Y-%m-%d")
        
        if not check_out_date:
            check_out = datetime.strptime(check_in_date, "%Y-%m-%d") + timedelta(days=2)
            check_out_date = check_out.strftime("%Y-%m-%d")
        
        # Step 1: Search hotels by city
        search_url = f"{self.base_url}/v1/reference-data/locations/hotels/by-city"
        headers = {"Authorization": f"Bearer {token}"}
        search_params = {
            "cityCode": city_code.upper()[:3],
            "radius": 50,  # 50km radius
            "radiusUnit": "KM",
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Get hotel IDs
                search_response = await client.get(search_url, headers=headers, params=search_params)
                
                if search_response.status_code != 200:
                    print(f"⚠️ Amadeus hotel search failed: {search_response.status_code}")
                    return []
                
                search_data = search_response.json()
                hotel_ids = [h.get("hotelId") for h in search_data.get("data", [])[:20]]
                
                if not hotel_ids:
                    return []
                
                # Step 2: Get hotel offers
                offers_url = f"{self.base_url}/v3/shopping/hotel-offers"
                offers_params = {
                    "hotelIds": ",".join(hotel_ids[:10]),  # Limit to 10 hotels per request
                    "adults": adults,
                    "checkInDate": check_in_date,
                    "checkOutDate": check_out_date,
                    "currency": "EUR",
                }
                
                offers_response = await client.get(offers_url, headers=headers, params=offers_params)
                
                if offers_response.status_code != 200:
                    print(f"⚠️ Amadeus hotel offers failed: {offers_response.status_code}")
                    return []
                
                offers_data = offers_response.json()
                hotels = []
                
                for hotel_data in offers_data.get("data", [])[:max_results]:
                    hotel_info = hotel_data.get("hotel", {})
                    offers = hotel_data.get("offers", [])
                    
                    if not offers:
                        continue
                    
                    # Get cheapest offer
                    cheapest = min(offers, key=lambda o: float(o.get("price", {}).get("total", 999999)))
                    price_per_night = int(float(cheapest.get("price", {}).get("total", 0)))
                    
                    # Filter by max price if specified
                    if max_price and price_per_night > max_price:
                        continue
                    
                    hotels.append({
                        "name": hotel_info.get("name", "Unknown Hotel"),
                        "rating": None,  # Amadeus doesn't always provide ratings
                        "price_per_night": price_per_night,
                        "currency": "EUR",
                        "address": hotel_info.get("address", {}).get("countryCode", ""),
                        "source": "amadeus",
                    })
                
                return hotels
        
        except Exception as e:
            print(f"⚠️ Amadeus hotel search error: {e}")
            return []
    
    def _format_duration(self, iso_duration: str) -> str:
        """
        Convert ISO 8601 duration (e.g., 'PT2H30M') to readable format (e.g., '2h 30m').
        """
        import re
        
        # Parse ISO duration: PT2H30M
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', iso_duration)
        if not match:
            return "?"
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        
        if hours and minutes:
            return f"{hours}h {minutes}m"
        elif hours:
            return f"{hours}h"
        elif minutes:
            return f"{minutes}m"
        else:
            return "?"
    
    async def get_iata_code(self, city_name: str) -> Optional[str]:
        """
        Get IATA airport/city code for a city name.
        Uses Amadeus Airport & City Search API.
        
        Args:
            city_name: City name (e.g., "Zagreb", "Athens")
        
        Returns:
            IATA code (e.g., "ZAG", "ATH") or None if not found
        """
        if not self.is_configured():
            return None
        
        token = await self._get_access_token()
        if not token:
            return None
        
        url = f"{self.base_url}/v1/reference-data/locations"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "subType": "CITY,AIRPORT",
            "keyword": city_name,
            "page[limit]": 1,
        }
        
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    return None
                
                data = response.json()
                locations = data.get("data", [])
                
                if locations:
                    return locations[0].get("iataCode")
                
                return None
        
        except Exception as e:
            print(f"⚠️ Amadeus IATA lookup error: {e}")
            return None

    async def search_flight_inspiration(
        self,
        origin: str,
        departure_date: Optional[str] = None,
        max_price: Optional[int] = None,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for cheapest flight destinations from origin using Flight Inspiration Search.
        Great for "where can I fly cheaply from Zagreb?" type queries.
        
        Args:
            origin: IATA airport code (e.g., "ZAG")
            departure_date: Optional departure date in YYYY-MM-DD format
            max_price: Optional maximum price in EUR
            max_results: Maximum number of destinations to return
        
        Returns:
            List of cheap destinations with prices
        """
        if not self.is_configured():
            return []
        
        token = await self._get_access_token()
        if not token:
            return []
        
        url = f"{self.base_url}/v1/shopping/flight-destinations"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "origin": origin.upper()[:3],
        }
        
        if departure_date:
            params["departureDate"] = departure_date
        if max_price:
            params["maxPrice"] = max_price
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    print(f"⚠️ Amadeus inspiration search failed: {response.status_code}")
                    return []
                
                data = response.json()
                destinations = []
                
                for item in data.get("data", [])[:max_results]:
                    price_info = item.get("price", {})
                    destinations.append({
                        "destination": item.get("destination", ""),
                        "departure_date": item.get("departureDate", ""),
                        "return_date": item.get("returnDate", ""),
                        "price": float(price_info.get("total", 0)),
                        "currency": "EUR",
                        "source": "amadeus_inspiration",
                    })
                
                print(f"✅ Amadeus found {len(destinations)} cheap destinations from {origin}")
                return destinations
        
        except Exception as e:
            print(f"⚠️ Amadeus inspiration search error: {e}")
            return []

    async def search_cheapest_dates(
        self,
        origin: str,
        destination: str,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for cheapest dates to fly between two cities using Flight Cheapest Date Search.
        Great for "when is cheapest to fly from Zagreb to London?" type queries.
        
        Args:
            origin: IATA airport code (e.g., "ZAG")
            destination: IATA airport code (e.g., "LON")
            max_results: Maximum number of date options to return
        
        Returns:
            List of cheapest date options with prices
        """
        if not self.is_configured():
            return []
        
        token = await self._get_access_token()
        if not token:
            return []
        
        url = f"{self.base_url}/v1/shopping/flight-dates"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "origin": origin.upper()[:3],
            "destination": destination.upper()[:3],
        }
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    print(f"⚠️ Amadeus cheapest dates search failed: {response.status_code}")
                    return []
                
                data = response.json()
                dates = []
                
                for item in data.get("data", [])[:max_results]:
                    price_info = item.get("price", {})
                    dates.append({
                        "departure_date": item.get("departureDate", ""),
                        "return_date": item.get("returnDate", ""),
                        "price": float(price_info.get("total", 0)),
                        "currency": "EUR",
                        "source": "amadeus_cheapest_dates",
                    })
                
                print(f"✅ Amadeus found {len(dates)} cheapest dates for {origin} → {destination}")
                return dates
        
        except Exception as e:
            print(f"⚠️ Amadeus cheapest dates error: {e}")
            return []

    async def search_points_of_interest(
        self,
        latitude: float,
        longitude: float,
        radius: int = 5,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for points of interest near a location using Amadeus POI API.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            radius: Search radius in km (default 5)
            max_results: Maximum number of POIs to return
        
        Returns:
            List of points of interest with details
        """
        if not self.is_configured():
            return []
        
        token = await self._get_access_token()
        if not token:
            return []
        
        url = f"{self.base_url}/v1/reference-data/locations/pois"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius,
            "page[limit]": max_results,
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    print(f"⚠️ Amadeus POI search failed: {response.status_code}")
                    return []
                
                data = response.json()
                pois = []
                
                for item in data.get("data", [])[:max_results]:
                    pois.append({
                        "name": item.get("name", ""),
                        "category": item.get("category", ""),
                        "subcategory": item.get("subCategory", ""),
                        "rank": item.get("rank", 0),
                        "latitude": item.get("geoCode", {}).get("latitude"),
                        "longitude": item.get("geoCode", {}).get("longitude"),
                        "source": "amadeus_poi",
                    })
                
                print(f"✅ Amadeus found {len(pois)} POIs")
                return pois
        
        except Exception as e:
            print(f"⚠️ Amadeus POI search error: {e}")
            return []


# Global instance
amadeus_client = AmadeusClient()
