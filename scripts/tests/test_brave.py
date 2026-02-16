import os
import requests
from dotenv import load_dotenv

REQUEST_TIMEOUT = int(os.getenv('HTTP_TIMEOUT_SECONDS', '30'))

def test_brave():
    load_dotenv()
    api_key = os.environ.get('BRAVE_SEARCH_API_KEY')
    if not api_key:
        print("Error: BRAVE_SEARCH_API_KEY not found.")
        return

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    params = {
        "q": "site:smokedbarbecuesource.com griddle",
        "count": 1
    }

    print(f"Testing Brave Search API...")
    try:
        # Run two requests quickly to test rate limit
        for i in range(3):
            print(f"Request {i+1}...")
            response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            print(f"Status: {response.status_code}")
            if response.status_code != 200:
                print(f"Error: {response.text}")
            # Do NOT sleep to trigger rate limit
    except Exception as e:
        print(f"Brave Test Failed: {e}")

if __name__ == "__main__":
    test_brave()
