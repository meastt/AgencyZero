#!/usr/bin/env python3
"""
GSC Audit Script - Pull performance data and identify opportunities
"""
import json
import os
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram_utils import send_telegram_alert
from dotenv import load_dotenv

# Load root .env
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../.env'))

# SITE_PREFIX support for multi-site
SITE_PREFIX = os.getenv('SITE_PREFIX', '')
if SITE_PREFIX:
    SITE_PREFIX += '_'

# Load credentials
creds_json = os.environ.get(f'{SITE_PREFIX}GSC_JSON_KEY', os.environ.get('GSC_JSON_KEY'))
if not creds_json:
    msg = ("🚨 *GSC AUDIT BLOCKED*\n"
           "• `GSC_JSON_KEY` not found in environment\n"
           "• Traffic drop detection and Page 2 analysis are offline\n"
           "• Action needed: set the service account JSON key")
    print(msg)
    send_telegram_alert(msg)
    exit(1)

try:
    creds_dict = json.loads(creds_json)
    # Fix double-escaped newlines in private key
    if 'private_key' in creds_dict:
        creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
    
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/webmasters.readonly']
    )
    service = build('searchconsole', 'v1', credentials=credentials)
except Exception as e:
    msg = (f"🚨 *GSC AUDIT AUTH FAILED*\n"
           f"• Error: `{str(e)[:200]}`\n"
           f"• Cannot authenticate with Google Search Console\n"
           f"• Check service account credentials")
    print(msg)
    send_telegram_alert(msg)
    exit(1)

# Site property (use SITE_PREFIX for multi-site support)
SITE_URL = os.getenv(f'{SITE_PREFIX}GSC_SITE_URL', os.getenv('GSC_SITE_URL', 'https://griddleking.com/'))

# Force URL-prefix property if domain property is detected
if SITE_URL.startswith('sc-domain:'):
    print(f"⚠️  Detecting domain property '{SITE_URL}'. Switching to authorized URL-prefix 'https://griddleking.com/'")
    SITE_URL = 'https://griddleking.com/'

print(f"🔍 SITE_URL: {SITE_URL}")

# Date ranges - last 28 days vs previous 28 days
end_date = datetime.now().date()
start_date = end_date - timedelta(days=28)
prev_start = start_date - timedelta(days=28)
prev_end = start_date - timedelta(days=1)

print(f"🔍 GSC AUDIT: {SITE_URL}")
print(f"Current period: {start_date} to {end_date}")
print(f"Previous period: {prev_start} to {prev_end}\n")

# Get current period data
current_request = {
    'startDate': str(start_date),
    'endDate': str(end_date),
    'dimensions': ['page'],
    'rowLimit': 100
}

try:
    current_response = service.searchanalytics().query(
        siteUrl=SITE_URL,
        body=current_request
    ).execute()
except Exception as e:
    msg = (f"🚨 *GSC AUDIT QUERY FAILED*\n"
           f"• Period: current ({start_date} to {end_date})\n"
           f"• Error: `{str(e)[:200]}`\n"
           f"• Traffic analysis is offline")
    print(msg)
    send_telegram_alert(msg)
    exit(1)

# Get previous period data
prev_request = {
    'startDate': str(prev_start),
    'endDate': str(prev_end),
    'dimensions': ['page'],
    'rowLimit': 100
}

try:
    prev_response = service.searchanalytics().query(
        siteUrl=SITE_URL,
        body=prev_request
    ).execute()
except Exception as e:
    msg = (f"🚨 *GSC AUDIT QUERY FAILED*\n"
           f"• Period: previous ({prev_start} to {prev_end})\n"
           f"• Error: `{str(e)[:200]}`\n"
           f"• Cannot compare traffic periods")
    print(msg)
    send_telegram_alert(msg)
    exit(1)

# Build comparison
current_pages = {}
if 'rows' in current_response:
    for row in current_response['rows']:
        url = row['keys'][0]
        current_pages[url] = {
            'clicks': row.get('clicks', 0),
            'impressions': row.get('impressions', 0),
            'ctr': row.get('ctr', 0),
            'position': row.get('position', 0)
        }

prev_pages = {}
if 'rows' in prev_response:
    for row in prev_response['rows']:
        url = row['keys'][0]
        prev_pages[url] = {
            'clicks': row.get('clicks', 0),
            'impressions': row.get('impressions', 0),
            'ctr': row.get('ctr', 0),
            'position': row.get('position', 0)
        }

# Find pages with significant drops
print("📉 PAGES WITH TRAFFIC DROPS (>10%):")
print("-" * 80)
drops = []
for url, current_data in current_pages.items():
    if url in prev_pages:
        prev_clicks = prev_pages[url]['clicks']
        current_clicks = current_data['clicks']
        if prev_clicks > 10:  # Only consider pages with meaningful traffic
            change_pct = ((current_clicks - prev_clicks) / prev_clicks) * 100
            if change_pct < -10:
                drops.append({
                    'url': url,
                    'prev_clicks': prev_clicks,
                    'current_clicks': current_clicks,
                    'change_pct': change_pct,
                    'position': current_data['position']
                })

drops.sort(key=lambda x: x['change_pct'])
for drop in drops[:10]:
    print(f"🔴 {drop['url']}")
    print(f"   Clicks: {drop['prev_clicks']:.0f} → {drop['current_clicks']:.0f} ({drop['change_pct']:.1f}%)")
    print(f"   Position: {drop['position']:.1f}\n")

# Find Page 2 opportunities (position 11-20)
print("\n🎯 PAGE 2 OPPORTUNITIES (Position 11-20):")
print("-" * 80)
page2_opps = []
for url, data in current_pages.items():
    if 11 <= data['position'] <= 20 and data['impressions'] > 100:
        page2_opps.append({
            'url': url,
            'position': data['position'],
            'clicks': data['clicks'],
            'impressions': data['impressions'],
            'ctr': data['ctr']
        })

page2_opps.sort(key=lambda x: x['impressions'], reverse=True)
for opp in page2_opps[:10]:
    print(f"🟡 {opp['url']}")
    print(f"   Position: {opp['position']:.1f} | Clicks: {opp['clicks']:.0f} | Impressions: {opp['impressions']:.0f}\n")

# Summary stats
total_current_clicks = sum(p['clicks'] for p in current_pages.values())
total_prev_clicks = sum(p['clicks'] for p in prev_pages.values())
overall_change = ((total_current_clicks - total_prev_clicks) / total_prev_clicks * 100) if total_prev_clicks > 0 else 0

print("\n📊 OVERALL STATS:")
print(f"Total clicks (current): {total_current_clicks:.0f}")
print(f"Total clicks (previous): {total_prev_clicks:.0f}")
print(f"Change: {overall_change:.1f}%")

# Save detailed data
output = {
    'timestamp': datetime.now().isoformat(),
    'drops': drops,
    'page2_opportunities': page2_opps,
    'summary': {
        'current_clicks': total_current_clicks,
        'prev_clicks': total_prev_clicks,
        'change_pct': overall_change
    }
}

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data')
os.makedirs(DATA_DIR, exist_ok=True)
# Use SITE_PREFIX in filename to avoid agents overwriting each other
raw_prefix = os.getenv('SITE_PREFIX', '')
file_slug = raw_prefix.lower().replace('wp_', '').replace('_', '') if raw_prefix else 'default'
output_path = os.path.join(DATA_DIR, f'gsc_audit_{file_slug}.json')

with open(output_path, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n✅ Data saved to {output_path}")
