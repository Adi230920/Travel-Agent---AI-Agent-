"""
backend/tools/kiwi_tool.py — AI Travel Agent
============================================

Fetches real-time flight and transport options using the Kiwi Tequila API.
Provides an accessible alternative to Amadeus with a robust sandbox.

Public API:
-----------
    search_flights(origin: str, destination: str, departure_date: str, return_date: str = None) -> list[dict]
"""

import logging
import os
import requests
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def _format_date(date_str: str) -> Optional[str]:
    """Convert ISO date (YYYY-MM-DD) to Kiwi format (DD/MM/YYYY)."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return None

def _get_location_id(city_name: str, api_key: str) -> Optional[str]:
    """Look up the Kiwi location ID or IATA code for a city."""
    url = "https://tequila-api.kiwi.com/locations/query"
    params = {
        "term": city_name,
        "location_types": "city",
        "limit": 1
    }
    headers = {"apikey": api_key}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("locations"):
                return data["locations"][0]["id"]
    except Exception as e:
        logger.error("kiwi_tool: Location lookup error: %s", e)
    
    return None

def search_flights(origin: str, destination: str, departure_date: str, return_date: str = None) -> List[Dict]:
    """
    Search for transport options (flights, etc.) using Kiwi Tequila.
    Returns a list of normalized flight offers.
    """
    api_key = os.getenv("KIWI_API_KEY", "").strip()
    if not api_key:
        logger.warning("kiwi_tool: KIWI_API_KEY missing. Transport search disabled.")
        return []

    # 1. Resolve location IDs
    origin_id = _get_location_id(origin, api_key)
    dest_id = _get_location_id(destination, api_key)

    if not origin_id or not dest_id:
        logger.warning("kiwi_tool: Could not resolve IDs for %s -> %s", origin, destination)
        return []

    # 2. Prepare Search
    url = "https://tequila-api.kiwi.com/v2/search"
    
    dep_date_kiwi = _format_date(departure_date)
    if not dep_date_kiwi:
        return []

    params = {
        "fly_from": origin_id,
        "fly_to": dest_id,
        "date_from": dep_date_kiwi,
        "date_to": dep_date_kiwi,
        "curr": "USD",
        "limit": 3,
        "one_for_city": 0,
        "only_working_days": 0,
        "delay": 0,
        "max_stopovers": 2
    }

    if return_date:
        ret_date_kiwi = _format_date(return_date)
        if ret_date_kiwi:
            params["return_from"] = ret_date_kiwi
            params["return_to"] = ret_date_kiwi

    headers = {"apikey": api_key}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=20)
        if response.status_code == 200:
            data = response.json()
            offers = data.get("data", [])
            
            results = []
            for offer in offers:
                # Basic normalization
                try:
                    results.append({
                        "carrier": offer.get("airlines", ["Multiple"])[0],
                        "price": f"{offer.get('price')} USD",
                        "duration": f"{int(offer.get('duration', {}).get('total', 0) / 3600)}h {int((offer.get('duration', {}).get('total', 0) % 3600) / 60)}m",
                        "departure": offer.get("local_departure", ""),
                        "arrival": offer.get("local_arrival", "")
                    })
                except Exception as ex:
                    logger.warning("kiwi_tool: Error parsing offer: %s", ex)
            
            return results
        else:
            logger.error("kiwi_tool: Search failed (HTTP %d): %s", response.status_code, response.text[:200])
    except Exception as e:
        logger.error("kiwi_tool: Search error: %s", e)

    return []

if __name__ == "__main__":
    # Manual verification
    import pprint
    logging.basicConfig(level=logging.INFO)
    print("Testing Kiwi search...")
    # Requires KIWI_API_KEY in environment
    res = search_flights("Mumbai", "London", "2026-06-15", "2026-06-25")
    pprint.pprint(res)
