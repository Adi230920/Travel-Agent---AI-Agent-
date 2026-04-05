"""
backend/tools/rapidapi_tool.py — AI Travel Agent
================================================

Uses RapidAPI (TripAdvisor wrapper) for location, flights, and restaurants.
Provides a unified platform for real-world travel data.

Public API:
-----------
    get_location_details(city_name: str) -> dict
    search_flights(origin_iata: str, dest_iata: str, dep_date: str, ret_date: str = None) -> list[dict]
    search_restaurants(location_id: str, limit: int = 5) -> list[dict]
"""

import logging
import os
import requests
import json
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def _get_headers() -> Dict[str, str]:
    """Base headers for RapidAPI requests."""
    try:
        from backend.config import RAPIDAPI_KEY
        api_key = RAPIDAPI_KEY
    except ImportError:
        api_key = os.getenv("RAPIDAPI_KEY", "").strip()

    if not api_key or "your_" in api_key:
        return {} # Mock mode indicator
    return {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "tripadvisor16.p.rapidapi.com",
        "Content-Type": "application/json"
    }

def get_location_details(city_name: str) -> Dict:
    """
    Look up a city on TripAdvisor to get its locationId and IATA code.
    Returns: {"locationId": "...", "iataCode": "...", "name": "..."} or {}
    """
    headers = _get_headers()
    if not headers:
        # MOCK MODE
        if "paris" in city_name.lower():
            return {"locationId": "187147", "iataCode": "CDG", "name": "Paris"}
        if "mumbai" in city_name.lower():
            return {"locationId": "304554", "iataCode": "BOM", "name": "Mumbai"}
        return {}

    url = "https://tripadvisor16.p.rapidapi.com/api/v1/hotels/searchLocation"
    params = {"query": city_name}
    headers = _get_headers()

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") and data.get("data"):
                # Usually returns a list of results
                results = data["data"]
                if results:
                    first = results[0]
                    # API can return 'locationId' or 'geoId' depending on the item type
                    loc_id = first.get("locationId") or first.get("geoId")
                    # Names sometimes contain <b> tags
                    raw_name = first.get("title", city_name)
                    clean_name = raw_name.replace("<b>", "").replace("</b>", "").strip()
                    
                    raw_iata = first.get("iataCode")
                    # Validate IATA (3 uppercase letters)
                    iata = raw_iata if (raw_iata and len(raw_iata) == 3 and raw_iata.isupper()) else None
                    
                    logger.info("rapidapi_tool: found location '%s' (ID: %s, IATA: %s)", clean_name, loc_id, iata)
                    
                    return {
                        "locationId": str(loc_id) if loc_id else None,
                        "iataCode": iata,
                        "name": clean_name
                    }
        else:
            logger.warning("rapidapi_tool: location search HTTP %d: %s", response.status_code, response.text[:200])
    except Exception as e:
        logger.error("rapidapi_tool: Location search error: %s", e)
    
    return {}

def search_restaurants(location_id: str, limit: int = 2) -> List[Dict]:
    """
    Search for top restaurants in a given location ID.
    """
    if not location_id:
        return []

    headers = _get_headers()
    if not headers:
        # MOCK MODE for locationId '187147' (Paris)
        if location_id == "187147":
            return [
                {"name": "Le Jules Verne", "price_level": "$$$$", "cuisine": "French, Gastronomy", "rating": "5.0", "description": "Eiffel Tower views"},
                {"name": "L'As du Fallafel", "price_level": "$", "cuisine": "Middle Eastern", "rating": "4.5", "description": "Iconic Marais street food"}
            ]
        return []

    url = "https://tripadvisor16.p.rapidapi.com/api/v1/restaurant/searchRestaurants"
    params = {"locationId": location_id}
    headers = _get_headers()

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") and data.get("data"):
                # Clean up results
                raw_list = data["data"].get("data", [])
                results = []
                for item in raw_list[:limit]:
                    results.append({
                        "name": item.get("name"),
                        "price_level": item.get("priceTag", "$$"),
                        "cuisine": ", ".join([c.get("name", "") for c in item.get("cuisine", [])[:2]]),
                        "rating": item.get("averageRating", "N/A"),
                        "description": item.get("establishmentTypeAndCuisineTags", ["Fine Dining"])[0]
                    })
                return results
    except Exception as e:
        logger.error("rapidapi_tool: Restaurant search error: %s", e)
    
    return []

def search_flights(origin_iata: str, dest_iata: str, dep_date: str, ret_date: str = None) -> List[Dict]:
    """
    Search for flight offers using TripAdvisor (RapidAPI).
    Note: Many TripAdvisor wrappers on RapidAPI use 'searchFlights' or 'search-roundtrip'.
    """
    # Assuming search-roundtrip based on common pattern
    url = "https://tripadvisor16.p.rapidapi.com/api/v1/flights/searchFlights"
    params = {
        "sourceAirportCode": origin_iata,
        "destinationAirportCode": dest_iata,
        "date": dep_date,
        "itineraryType": "ONE_WAY" if not ret_date else "ROUND_TRIP",
        "sortOrder": "PRICE",
        "numAdults": "1",
        "classOfService": "ECONOMY"
    }
    
    if ret_date:
        params["returnDate"] = ret_date

    headers = _get_headers()
    if not headers:
        # MOCK MODE
        return [{
            "carrier": "Air France",
            "price": "450 USD",
            "duration": "10h 30m",
            "departure": "2026-06-15T12:00:00",
            "arrival": "2026-06-15T22:30:00"
        }]

    if len(origin_iata) != 3 or len(dest_iata) != 3:
        logger.warning("rapidapi_tool: skipping flight search — invalid IATA codes: %s -> %s", origin_iata, dest_iata)
        return []

    try:
        # Tripadvisor searches are often async, this wrapper might handle it or return a searchKey
        response = requests.get(url, headers=headers, params=params, timeout=20)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") and data.get("data"):
                # Standardize output
                flights_data = data["data"].get("flights", [])
                results = []
                for f in flights_data[:3]:
                    # Extract carrier from nested structure
                    segments = f.get("segments", [])
                    carrier = "Multiple"
                    if segments:
                        legs = segments[0].get("legs", [])
                        if legs:
                            carrier = legs[0].get("carrierName", "Multiple")

                    purchase_links = f.get("purchaseLinks", [])
                    price = purchase_links[0].get("totalPrice", "N/A") if purchase_links else "N/A"

                    results.append({
                        "carrier": carrier,
                        "price": price,
                        "duration": f.get("totalDuration", "N/A"),
                        "departure": f.get("departureTime", ""),
                        "arrival": f.get("arrivalTime", "")
                    })
                
                logger.info("rapidapi_tool: found %d flights from %s to %s", len(results), origin_iata, dest_iata)
                return results
    except Exception as e:
        logger.error("rapidapi_tool: Flight search error: %s", e)

    return []

if __name__ == "__main__":
    # Internal Tool Test
    import pprint
    from dotenv import load_dotenv
    load_dotenv() # Load from .env for local testing
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    
    print("\n--- Testing Location Lookup (Paris) ---")
    loc = get_location_details("Paris")
    pprint.pprint(loc)
    
    print("\n--- Testing Location Lookup (London) ---")
    loc_london = get_location_details("London")
    pprint.pprint(loc_london)
    
    if loc.get("locationId"):
        print("\n--- Testing Restaurant Lookup ---")
        res = search_restaurants(loc["locationId"], limit=2)
        pprint.pprint(res)
    
    print("\n--- Testing Location Lookup (Mumbai) ---")
    loc_mumbai = get_location_details("Mumbai")
    pprint.pprint(loc_mumbai)
    
    if loc_mumbai.get("iataCode") and loc_london.get("iataCode"):
        print("\n--- Testing Flight Search (BOM -> LHR) ---")
        flights = search_flights(loc_mumbai["iataCode"], loc_london["iataCode"], "2026-06-15")
        pprint.pprint(flights)
