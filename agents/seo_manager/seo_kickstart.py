#!/usr/bin/env python3
"""
SEO Kickstart Mission for Griddle King
Analyzes GSC data, competitors, content decay, and internal linking
"""

import os
import json
import requests
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from collections import defaultdict
import time

# Configuration
SITE_URL = os.getenv('GSC_SITE_URL', 'https://griddleking.com/')
WP_URL = 'https://griddleking.com'  # Override to use Griddle King
WP_USERNAME = os.getenv('WP_USERNAME')
WP_APP_PASS = os.getenv('WP_APP_PASS')
BRAVE_API_KEY = os.getenv('BRAVE_SEARCH_API_KEY')
GSC_JSON_KEY = os.getenv('GSC_JSON_KEY')

# Parse GSC credentials
gsc_creds = json.loads(GSC_JSON_KEY)
credentials = service_account.Credentials.from_service_account_info(
    gsc_creds,
    scopes=['https://www.googleapis.com/auth/webmasters.readonly']
)

# Initialize GSC client
gsc_service = build('searchconsole', 'v1', credentials=credentials)

print("🚀 SEO KICKSTART MISSION - GRIDDLE KING\n")

# ============================================================================
# 1. GSC TRAFFIC ANALYSIS
# ============================================================================
print("📊 STEP 1: GSC Traffic Analysis (Last 90 Days)")
print("=" * 60)

end_date = datetime.now().date()
start_date_recent = end_date - timedelta(days=45)  # Last 45 days
start_date_comparison = end_date - timedelta(days=90)  # Previous 45 days
mid_date = end_date - timedelta(days=45)

def query_gsc(start, end, dimensions=['page']):
    """Query GSC API"""
    request = {
        'startDate': start.strftime('%Y-%m-%d'),
        'endDate': end.strftime('%Y-%m-%d'),
        'dimensions': dimensions,
        'rowLimit': 25000
    }
    response = gsc_service.searchanalytics().query(
        siteUrl=SITE_URL, 
        body=request
    ).execute()
    return response.get('rows', [])

# Get recent and comparison data
print(f"Querying recent period: {start_date_recent} to {end_date}")
recent_data = query_gsc(start_date_recent, end_date)

print(f"Querying comparison period: {start_date_comparison} to {mid_date}")
comparison_data = query_gsc(start_date_comparison, mid_date)

# Build comparison dict
comparison_clicks = {}
for row in comparison_data:
    page = row['keys'][0]
    comparison_clicks[page] = row['clicks']

# Analyze declines
declining_pages = []
for row in recent_data:
    page = row['keys'][0]
    recent_clicks = row['clicks']
    old_clicks = comparison_clicks.get(page, 0)
    
    if old_clicks >= 100:  # High-value pages only
        if old_clicks > 0:
            decline_pct = ((recent_clicks - old_clicks) / old_clicks) * 100
            if decline_pct < -10:  # >10% decline
                declining_pages.append({
                    'page': page,
                    'recent_clicks': recent_clicks,
                    'old_clicks': old_clicks,
                    'decline_pct': decline_pct,
                    'impressions': row.get('impressions', 0),
                    'ctr': row.get('ctr', 0) * 100,
                    'position': row.get('position', 0)
                })

declining_pages.sort(key=lambda x: x['old_clicks'], reverse=True)

print(f"\n✅ Found {len(declining_pages)} high-value pages with >10% decline:")
for i, page in enumerate(declining_pages[:10], 1):
    print(f"{i}. {page['page']}")
    print(f"   Clicks: {page['old_clicks']:.0f} → {page['recent_clicks']:.0f} ({page['decline_pct']:.1f}%)")
    print(f"   Position: {page['position']:.1f}, CTR: {page['ctr']:.2f}%")

# ============================================================================
# 2. WORDPRESS CONTENT AUDIT
# ============================================================================
print("\n📝 STEP 2: WordPress Content Audit")
print("=" * 60)

# Get all published posts
wp_auth = (WP_USERNAME, WP_APP_PASS)
all_posts = []
page = 1

print("Fetching WordPress posts...")
while True:
    response = requests.get(
        f"{WP_URL}/wp-json/wp/v2/posts",
        params={'per_page': 100, 'page': page, 'status': 'publish'},
        auth=wp_auth
    )
    if response.status_code != 200:
        break
    posts = response.json()
    if not posts:
        break
    all_posts.extend(posts)
    page += 1
    time.sleep(0.5)

print(f"✅ Retrieved {len(all_posts)} published posts")

# Build post database
post_db = {}
for post in all_posts:
    post_db[post['link']] = {
        'id': post['id'],
        'title': post['title']['rendered'],
        'date': post['date'],
        'modified': post['modified'],
        'link': post['link'],
        'content': post['content']['rendered']
    }

# Identify old posts (>12 months)
one_year_ago = datetime.now() - timedelta(days=365)
old_posts = []

for url, post in post_db.items():
    post_date = datetime.strptime(post['date'], '%Y-%m-%dT%H:%M:%S')
    age_days = (datetime.now() - post_date).days
    if age_days > 365:
        old_posts.append({
            'url': url,
            'title': post['title'],
            'age_days': age_days,
            'date': post['date']
        })

print(f"✅ Found {len(old_posts)} posts >12 months old")

# Cross-reference with declining pages
print("\n🔍 STEP 3: Content Decay Detection")
print("=" * 60)

decay_candidates = []
for declining_page in declining_pages:
    page_url = declining_page['page']
    if page_url in post_db:
        post = post_db[page_url]
        post_date = datetime.strptime(post['date'], '%Y-%m-%dT%H:%M:%S')
        age_days = (datetime.now() - post_date).days
        
        if age_days > 365:
            decay_candidates.append({
                **declining_page,
                'title': post['title'],
                'age_days': age_days,
                'date': post['date']
            })

decay_candidates.sort(key=lambda x: x['old_clicks'], reverse=True)

print(f"✅ Found {len(decay_candidates)} declining pages that are >1 year old:")
for i, page in enumerate(decay_candidates[:5], 1):
    print(f"{i}. {page['title']}")
    print(f"   URL: {page['page']}")
    print(f"   Age: {page['age_days']} days | Clicks: {page['old_clicks']:.0f} → {page['recent_clicks']:.0f}")

# ============================================================================
# 4. INTERNAL LINKING AUDIT
# ============================================================================
print("\n🔗 STEP 4: Internal Linking Audit")
print("=" * 60)

# Build internal link graph
internal_links = defaultdict(set)  # page -> set of pages it links to
backlinks = defaultdict(set)  # page -> set of pages linking to it

for url, post in post_db.items():
    content = post['content']
    # Find internal links in content
    for target_url in post_db.keys():
        if target_url != url and target_url in content:
            internal_links[url].add(target_url)
            backlinks[target_url].add(url)

# Find orphaned content (no internal links)
orphaned = []
for url, post in post_db.items():
    backlink_count = len(backlinks.get(url, set()))
    if backlink_count == 0:
        orphaned.append({
            'url': url,
            'title': post['title'],
            'backlinks': 0
        })

print(f"✅ Found {len(orphaned)} orphaned posts (zero internal links):")
for i, orphan in enumerate(orphaned[:10], 1):
    print(f"{i}. {orphan['title']}")
    print(f"   {orphan['url']}")

# Identify high-authority posts (most outbound links)
high_authority = []
for url, post in post_db.items():
    outbound_count = len(internal_links.get(url, set()))
    backlink_count = len(backlinks.get(url, set()))
    if outbound_count > 5:  # Posts that already link to others
        high_authority.append({
            'url': url,
            'title': post['title'],
            'outbound': outbound_count,
            'backlinks': backlink_count
        })

high_authority.sort(key=lambda x: x['outbound'], reverse=True)

print(f"\n✅ Top 10 high-authority posts (most internal links):")
for i, post in enumerate(high_authority[:10], 1):
    print(f"{i}. {post['title']}")
    print(f"   Outbound: {post['outbound']} | Backlinks: {post['backlinks']}")

# ============================================================================
# 5. SAVE RESULTS
# ============================================================================
print("\n💾 Saving results to JSON...")

results = {
    'generated_at': datetime.now().isoformat(),
    'declining_pages': declining_pages[:20],
    'decay_candidates': decay_candidates[:10],
    'orphaned_posts': orphaned[:20],
    'high_authority_posts': high_authority[:10],
    'stats': {
        'total_posts': len(all_posts),
        'old_posts': len(old_posts),
        'orphaned_count': len(orphaned),
        'declining_count': len(declining_pages)
    }
}

with open('seo_kickstart_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("✅ Results saved to seo_kickstart_results.json")
print("\n🎯 Mission Step 1-4 Complete! Now analyzing keywords...")
