"""
backend/tools/image_tool.py — AI Travel Agent
==============================================

Fetches high-quality travel photos from the Unsplash API.
Used for destination recommendations and itinerary days.

Public API:
-----------
    search_image(query: str) -> str | None
"""

import logging
import os
import requests
from typing import Optional

logger = logging.getLogger(__name__)

# Fallback images for common travel themes if API fails/missing
_FALLBACK_IMAGES = {
    "beach": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200q=80",
    "mountain": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1200q=80",
    "city": "https://images.unsplash.com/photo-1449824913935-59a10b8d2000?auto=format&fit=crop&w=1200q=80",
    "default": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=1200q=80"
}

def search_image(query: str) -> Optional[str]:
    """
    Search Unsplash for an image matching the query.
    Returns the URL of the image, or a fallback URL if not found/error.
    """
    try:
        from backend.config import UNSPLASH_ACCESS_KEY
        access_key = UNSPLASH_ACCESS_KEY
    except ImportError:
        access_key = os.getenv("UNSPLASH_ACCESS_KEY", "").strip()
    
    if not access_key:
        logger.warning("image_tool: UNSPLASH_ACCESS_KEY missing. Using fallback.")
        return _get_fallback(query)

    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "per_page": 1,
        "orientation": "landscape",
        "client_id": access_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                # Return the regular size URL
                image_url = data["results"][0]["urls"]["regular"]
                logger.info("image_tool: Found image for query '%s'", query)
                return image_url
            else:
                logger.warning("image_tool: No results for query '%s'", query)
        else:
            logger.error("image_tool: Unsplash API returned HTTP %d", response.status_code)
    except Exception as e:
        logger.error("image_tool: Error fetching image: %s", e)

    return _get_fallback(query)

def _get_fallback(query: str) -> str:
    """Choose a fallback image based on keywords in the query."""
    q = query.lower()
    if "beach" in q or "ocean" in q or "island" in q:
        return _FALLBACK_IMAGES["beach"]
    if "mountain" in q or "hiking" in q or "snow" in q:
        return _FALLBACK_IMAGES["mountain"]
    if "city" in q or "urban" in q or "street" in q:
        return _FALLBACK_IMAGES["city"]
    return _FALLBACK_IMAGES["default"]

if __name__ == "__main__":
    # Quick manual test
    import pprint
    logging.basicConfig(level=logging.INFO)
    print("Testing image search...")
    img = search_image("Paris Eiffel Tower")
    print(f"Result: {img}")
