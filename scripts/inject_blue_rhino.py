#!/usr/bin/env python3
"""
Targeted Link Injection: Blue Rhino vs Blackstone Post
Uses specific find/replace to inject contextual links to orphans.
"""

import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

WP_URL = os.getenv('WP_URL').rstrip('/')
WP_USERNAME = os.getenv('WP_USERNAME')
WP_APP_PASS = os.getenv('WP_APP_PASS')
REQUEST_TIMEOUT = int(os.getenv('HTTP_TIMEOUT_SECONDS', '30'))

def inject_links():
    base_url = f'{WP_URL}/wp-json/wp/v2'
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASS)
    
    # Fetch post
    slug = 'blue-rhino-razor-vs-blackstone-griddle'
    url = f'{base_url}/posts?slug={slug}'
    response = requests.get(url, auth=auth, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    post = response.json()[0]
    
    post_id = post['id']
    content = post['content']['rendered']
    original_content = content
    
    print("🎯 BLUE RHINO VS BLACKSTONE - Link Injection")
    print("="*80)
    
    # Define link insertions
    # Strategy: Add links after key phrases that naturally lead to related content
    
    injections = [
        {
            'find': 'Whether you\'re a seasoned grill master or just getting started',
            'replace': 'Whether you\'re a seasoned grill master or <a href="https://griddleking.com/electric-griddle-setup-guide-2025-complete-installation-first-use/">just getting started with your first griddle</a>',
            'orphan': 'Electric Griddle Setup Guide 2026'
        },
        {
            'find': 'shopping for options',
            'replace': 'shopping for options (check out our <a href="https://griddleking.com/commercial-vs-residential-griddles-2025-complete-buying-guide/">complete buying guide comparing commercial vs residential griddles</a>)',
            'orphan': 'Commercial vs Residential Griddles Buying Guide'
        },
        {
            'find': 'outdoor cooking game with a full line of grills, griddles, accessories',
            'replace': 'outdoor cooking game with a full line of grills, griddles (including <a href="https://griddleking.com/best-electric-outdoor-griddles-2025-complete-reviews-guide/">electric outdoor options</a>), accessories',
            'orphan': 'Best Electric Outdoor Griddles 2026'
        }
    ]
    
    changes_made = []
    
    for injection in injections:
        find_text = injection['find']
        replace_text = injection['replace']
        orphan_name = injection['orphan']
        
        if find_text in content:
            content = content.replace(find_text, replace_text, 1)
            changes_made.append(orphan_name)
            print(f"✅ Injected link to: {orphan_name}")
        else:
            print(f"❌ Context not found for: {orphan_name}")
            print(f"   Searched for: {find_text[:60]}...")
    
    # Update post if changes were made
    if len(changes_made) > 0:
        print(f"\n🔧 Updating post with {len(changes_made)} new links...")
        
        update_url = f'{base_url}/posts/{post_id}'
        response = requests.post(
            update_url,
            json={'content': content},
            auth=auth,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        
        result = {
            'success': True,
            'post_id': post_id,
            'post_url': 'https://griddleking.com/blue-rhino-razor-vs-blackstone-griddle/',
            'links_injected': len(changes_made),
            'orphans_rescued': changes_made,
            'timestamp': datetime.now().isoformat()
        }
        
        print("✅ POST UPDATED SUCCESSFULLY!")
        print(f"\n📊 Rescued {len(changes_made)} orphans:")
        for orphan in changes_made:
            print(f"  - {orphan}")
        
        # Save log
        with open('data/link_injection_log_batch2.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        return result
    else:
        print("\n⚠️  No matches found - content may have changed")
        return {'success': False, 'message': 'No matches found'}

if __name__ == '__main__':
    result = inject_links()
    print("\n" + "="*80)
    print(json.dumps(result, indent=2))
