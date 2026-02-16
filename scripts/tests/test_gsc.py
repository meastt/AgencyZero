import os
import json
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

def test_gsc():
    load_dotenv()
    
    key_str = os.environ.get('GSC_JSON_KEY')
    if not key_str:
        print("Error: GSC_JSON_KEY not found in environment.")
        return

    try:
        service_account_info = json.loads(key_str)
        if 'private_key' in service_account_info:
            service_account_info['private_key'] = service_account_info['private_key'].replace('\\n', '\n')
        
        scopes = ['https://www.googleapis.com/auth/webmasters.readonly']
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=scopes
        )

        service = build('searchconsole', 'v1', credentials=credentials)
        site_url = 'sc-domain:griddleking.com'
        
        print(f"Testing GSC for site: {site_url}")
        print(f"Service Account: {service_account_info.get('client_email')}")
        
        # Simple test: list sites
        sites = service.sites().list().execute()
        print("Accessible sites:")
        for site in sites.get('siteEntry', []):
            print(f"- {site['siteUrl']}")
            
        # Test query
        print(f"\nPerforming query for: {site_url}")
        from datetime import datetime, timedelta
        end_date = datetime.now().date() - timedelta(days=3)
        start_date = end_date - timedelta(days=28)
        
        request = {
            'startDate': str(start_date),
            'endDate': str(end_date),
            'dimensions': ['query'],
            'rowLimit': 5
        }
        
        response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
        print("Query successful!")
        print(json.dumps(response, indent=2))
            
    except Exception as e:
        print(f"GSC Test Failed: {e}")

if __name__ == "__main__":
    test_gsc()
