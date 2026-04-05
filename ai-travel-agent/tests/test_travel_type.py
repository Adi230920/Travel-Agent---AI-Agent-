import sys
import os
import logging
from pprint import pprint

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.recommendation_agent import get_recommendations

def test_domestic_mumbai():
    print("\n--- Testing Domestic Recommendations (Mumbai) ---")
    preferences = {
        "origin_city": "Mumbai",
        "travel_type": "domestic",
        "budget": "medium",
        "duration": 5,
        "travel_style": "cultural",
        "weather_preference": "warm"
    }
    recs = get_recommendations(preferences, {})
    pprint(recs)
    
    # Check if all destinations are in India
    for r in recs:
        if r['country'].lower() != "india":
            print(f"❌ FAILED: Found non-domestic destination: {r['destination']}, {r['country']}")
            return False
    print("✅ PASSED: All destinations are domestic.")
    return True

def test_international_mumbai():
    print("\n--- Testing International Recommendations (Mumbai) ---")
    preferences = {
        "origin_city": "Mumbai",
        "travel_type": "international",
        "budget": "medium",
        "duration": 5,
        "travel_style": "cultural",
        "weather_preference": "warm"
    }
    recs = get_recommendations(preferences, {})
    pprint(recs)
    
    # Check if all destinations are NOT in India
    for r in recs:
        if r['country'].lower() == "india":
            print(f"❌ FAILED: Found domestic destination in international request: {r['destination']}, {r['country']}")
            return False
    print("✅ PASSED: All destinations are international.")
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = True
    if not test_domestic_mumbai(): success = False
    if not test_international_mumbai(): success = False
    
    if success:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED.")
        sys.exit(1)
