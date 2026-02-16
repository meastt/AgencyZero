#!/usr/bin/env python3
"""
Batch 5: Link Injection - 5 Must-Do Steps First Use (6 backlinks)
Focus on first-time setup, seasoning, and temperature themes
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
    slug = '5-must-do-steps-for-the-first-griddle-use'
    url = f'{base_url}/posts?slug={slug}'
    response = requests.get(url, auth=auth, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    post = response.json()[0]
    
    post_id = post['id']
    content = post['content']['rendered']
    original_content = content
    
    print("🎯 5 MUST-DO STEPS - Link Injection (6 backlinks)")
    print("="*80)
    
    # Strategic injections for first-time setup context
    injections = [
        {
            'find': 'This is WAY more important than stressing over the first thing to cook on Blackstone Griddle.',
            'replace': 'This is WAY more important than stressing over <a href="https://griddleking.com/15-easy-griddle-breakfast-ideas-to-start-2025-right/">the first thing to cook on Blackstone Griddle</a>.',
            'orphan': '15 Easy Griddle Breakfast Ideas'
        },
        {
            'find': 'where your griddles heat zones are.',
            'replace': 'where your <a href="https://griddleking.com/griddle-temperature-control-guide-2025-master-your-heat-zones/">griddles heat zones</a> are.',
            'orphan': 'Griddle Temperature Control Guide 2026'
        },
        {
            'find': "Cooking on a griddle is a blast and to be honest, there isn't much your griddle cant do",
            'replace': 'Cooking on a griddle is a blast (see our <a href="https://griddleking.com/griddle-cooking-tips-essential-techniques-for-2025/">essential cooking tips and techniques</a>) and to be honest, there isn\'t much your griddle cant do',
            'orphan': 'Griddle Cooking Tips: Essential Techniques'
        },
        {
            'find': 'Next thing you know, you will be enjoying your self-made feast after cooking on a Blackstone Griddle for the first time.',
            'replace': 'Next thing you know, you will be enjoying your self-made feast after <a href="https://griddleking.com/best-flat-top-grill-recipes-for-beginners/">cooking on a Blackstone Griddle for the first time</a>.',
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
            'post_url': 'https://griddleking.com/5-must-do-steps-for-the-first-griddle-use/',
            'post_authority': '6 backlinks',
            'links_injected': len(changes_made),
            'orphans_rescued': changes_made,
            'timestamp': datetime.now().isoformat()
        }
        
        print("✅ POST UPDATED SUCCESSFULLY!")
        print(f"\n📊 Rescued {len(changes_made)} orphans:")
        for orphan in changes_made:
            print(f"  - {orphan}")
        
        # Save log
        with open('data/link_injection_log_batch5.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        return result
    else:
        print("\n⚠️  No matches found - content may have changed")
        return {'success': False, 'message': 'No matches found'}

if __name__ == '__main__':
    result = inject_links()
    print("\n" + "="*80)
    print(json.dumps(result, indent=2))
