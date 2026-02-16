#!/usr/bin/env python3
"""
Batch 4: Link Injection - 7 Portable Griddles (8 backlinks)
Focus on camping/portable/setup themes
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
    slug = '7-portable-griddles-for-the-great-outdoors'
    url = f'{base_url}/posts?slug={slug}'
    response = requests.get(url, auth=auth, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    post = response.json()[0]
    
    post_id = post['id']
    content = post['content']['rendered']
    original_content = content
    
    print("🎯 7 PORTABLE GRIDDLES - Link Injection (8 backlinks)")
    print("="*80)
    
    # Strategic injections for camping/portable context
    injections = [
        {
            'find': 'Bacon, eggs, hashbrowns and pancakes all at the same time?',
            'replace': '<a href="https://griddleking.com/15-easy-griddle-breakfast-ideas-to-start-2025-right/">Bacon, eggs, hashbrowns and pancakes</a> all at the same time?',
            'orphan': '15 Easy Griddle Breakfast Ideas'
        },
        {
            'find': 'Blackstone introduced a new indoor-use approved electric griddle',
            'replace': 'Blackstone introduced a new <a href="https://griddleking.com/electric-griddle-setup-guide-2025-complete-installation-first-use/">indoor-use approved electric griddle</a>',
            'orphan': 'Electric Griddle Setup Guide 2026'
        },
        {
            'find': 'A cold-rolled/cast-iron cooking surface will require a seasoning process',
            'replace': 'A cold-rolled/cast-iron cooking surface will require a <a href="https://griddleking.com/5-must-do-steps-for-the-first-griddle-use/">seasoning process</a>',
            'orphan': '5 Must-Do Steps First Griddle Use'
        },
        {
            'find': 'a trusty griddle at your side. That, my friends, is where memories are made',
            'replace': 'a trusty griddle at your side (check out our <a href="https://griddleking.com/best-flat-top-grill-recipes-for-beginners/">best recipes for beginners</a>). That, my friends, is where memories are made',
            'orphan': 'Best Flat Top Grill Recipes for Beginners'
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
            'post_url': 'https://griddleking.com/7-portable-griddles-for-the-great-outdoors/',
            'post_authority': '8 backlinks',
            'links_injected': len(changes_made),
            'orphans_rescued': changes_made,
            'timestamp': datetime.now().isoformat()
        }
        
        print("✅ POST UPDATED SUCCESSFULLY!")
        print(f"\n📊 Rescued {len(changes_made)} orphans:")
        for orphan in changes_made:
            print(f"  - {orphan}")
        
        # Save log
        with open('data/link_injection_log_batch4.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        return result
    else:
        print("\n⚠️  No matches found - content may have changed")
        return {'success': False, 'message': 'No matches found'}

if __name__ == '__main__':
    result = inject_links()
    print("\n" + "="*80)
    print(json.dumps(result, indent=2))
