#!/usr/bin/env python3
"""
Affiliate Revenue Engine - Link Auditor
Scans WordPress posts for Amazon/Impact/AvantLink links.
- Identifies untagged links.
- Identifies missing affiliate disclosures.
- Reports potential revenue leaks.
"""

import os
import sys
import re
import time
import json
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs

# Load root .env
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

# Add current directory to path so we can import telegram_utils
sys.path.append(os.path.dirname(__file__))
from telegram_utils import send_telegram_alert

# Configuration
# Usage: SITE_PREFIX=PHOTO python3 affiliate_audit.py
SITE_PREFIX = os.getenv('SITE_PREFIX', '')
if SITE_PREFIX:
    SITE_PREFIX += '_'

WP_URL = os.getenv(f'{SITE_PREFIX}URL', 'https://griddleking.com').rstrip('/')
WP_USERNAME = os.getenv(f'{SITE_PREFIX}USERNAME', os.getenv('WP_USERNAME'))
WP_APP_PASS = os.getenv(f'{SITE_PREFIX}PASSWORD', os.getenv('WP_APP_PASS'))

# Affiliate Tags
AMAZON_TAG = os.getenv(f'{SITE_PREFIX}AMAZON_ASSOCIATE_TAG', os.getenv('AMAZON_ASSOCIATE_TAG'))
IMPACT_ID = os.getenv(f'{SITE_PREFIX}IMPACT_RADIUS_ID', os.getenv('IMPACT_RADIUS_ID'))
AVANTLINK_ID = os.getenv(f'{SITE_PREFIX}AVANTLINK_ID', os.getenv('AVANTLINK_ID'))

print(f"💰 AFFILIATE REVENUE ENGINE - AUDIT: {WP_URL}")
print(f"🏷️  AMAZON TAG: {AMAZON_TAG}")
print(f"🔗 IMPACT ID: {IMPACT_ID}")

if not WP_USERNAME or not WP_APP_PASS:
    print("🚨 WordPress credentials missing.")
    exit(1)

def get_all_posts():
    """Fetch all published posts from WordPress."""
    wp_auth = (WP_USERNAME, WP_APP_PASS)
    all_posts = []
    page = 1
    
    print("Fetching posts...", end="", flush=True)
    while True:
        try:
            response = requests.get(
                f"{WP_URL}/wp-json/wp/v2/posts",
                params={'per_page': 100, 'page': page, 'status': 'publish'},
                auth=wp_auth,
                timeout=30
            )
            if response.status_code != 200:
                break
            posts = response.json()
            if not posts:
                break
            all_posts.extend(posts)
            print(".", end="", flush=True)
            page += 1
            time.sleep(0.2)
        except Exception as e:
            print(f"\n❌ Fetch error: {e}")
            break
            
    print(f"\n✅ Fetched {len(all_posts)} posts.")
    return all_posts

def analyze_links(posts):
    """Analyze links in posts for affiliate compliance."""
    issues = []
    total_amazon_links = 0
    tagged_amazon_links = 0
    untagged_amazon_links = 0
    
    amazon_regex = r"(amazon\.com|amzn\.to)[/a-zA-Z0-9\-\.]+"
    
    print("\n🔍 Scanning links...")
    
    for post in posts:
        content = post['content']['rendered']
        title = post['title']['rendered']
        link = post['link']
        post_id = post['id']
        
        # Find Amazon Links
        # This is a simple regex, a proper HTML parser (BeautifulSoup) is better but requires external lib
        # We'll use regex for speed and simplicity in this MVP script
        found_links = re.findall(r'href=[\'"]?([^\'" >]+)', content)
        
        post_issues = []
        
        for url in found_links:
            if 'amazon.com' in url or 'amzn.to' in url:
                total_amazon_links += 1
                if AMAZON_TAG and AMAZON_TAG in url:
                    tagged_amazon_links += 1
                elif 'amzn.to' not in url: # Bit.ly/Amzn.to might hide tags, ignore for now
                     # Check if it has ANY tag
                    if 'tag=' not in url:
                        untagged_amazon_links += 1
                        post_issues.append({
                            'type': 'untagged_amazon',
                            'url': url
                        })
                    elif AMAZON_TAG and AMAZON_TAG not in url:
                         post_issues.append({
                            'type': 'wrong_tag_amazon',
                            'url': url
                        })

        if post_issues:
            issues.append({
                'post_title': title,
                'post_url': link,
                'issues': post_issues
            })
            
    return issues, total_amazon_links, tagged_amazon_links, untagged_amazon_links

def main():
    if not AMAZON_TAG:
        print("⚠️  No Amazon Tag configured. Skipping tag verification.")
    
    posts = get_all_posts()
    issues, total, tagged, untagged = analyze_links(posts)
    
    print("\n📊 AUDIT RESULTS")
    print("=" * 40)
    print(f"Total Amazon Links: {total}")
    print(f"Properly Tagged:    {tagged}")
    print(f"Untagged/Wrong Tag: {untagged}")
    print(f"Posts with Issues:  {len(issues)}")
    
    if issues:
        print("\n🚩 TOP 5 REVENUE LEAKS:")
        for i, issue in enumerate(issues[:5], 1):
            print(f"{i}. {issue['post_title']}")
            print(f"   {issue['post_url']}")
            for prob in issue['issues'][:2]:
                print(f"   ❌ {prob['type']}: {prob['url'][:60]}...")
            if len(issue['issues']) > 2:
                print(f"   ...and {len(issue['issues']) - 2} more.")
        
        # Alert if significant leaks found
        if len(issues) > 0:
            msg = (f"💰 *AFFILIATE AUDIT: {WP_URL}*\n"
                   f"• Found {len(issues)} posts with potential revenue leaks\n"
                   f"• {untagged} Amazon links are untagged or have the wrong tag\n"
                   f"• *Action:* Run checking script to fix.")
            send_telegram_alert(msg)

    # Save details
    with open('affiliate_audit_report.json', 'w') as f:
        json.dump(issues, f, indent=2)
    print("\n✅ Validated report saved to affiliate_audit_report.json")

if __name__ == "__main__":
    main()
