#!/usr/bin/env python3
"""
Targeted Link Injection: Griddle vs Grill 2026 Post (12 backlinks - HIGH VALUE)
Strategic orphan rescue with breakfast and cooking tips focus.
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
    slug = 'griddle-vs-grill-debate-solved'
    url = f'{base_url}/posts?slug={slug}'
    response = requests.get(url, auth=auth, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    post = response.json()[0]
    
    post_id = post['id']
    content = post['content']['rendered']
    original_content = content
    
    print("🎯 GRIDDLE VS GRILL 2026 - High-Authority Link Injection")
    print("="*80)
    
    # Strategic injections targeting orphans with breakfast/cooking themes
    injections = [
        {
            'find': 'You can prepare breakfast favorites like pancakes, eggs, and bacon',
            'replace': 'You can prepare <a href="https://griddleking.com/15-easy-griddle-breakfast-ideas-to-start-2025-right/">breakfast favorites like pancakes, eggs, and bacon</a>',
            'orphan': '15 Easy Griddle Breakfast Ideas'
        },
        {
            'find': 'alongside lunch and dinner options such as stir-fries, quesadillas, smash burgers',
            'replace': 'alongside lunch and dinner options (check our <a href="https://griddleking.com/best-flat-top-grill-recipes-for-beginners/">best flat top grill recipes for beginners</a>) such as stir-fries, quesadillas, smash burgers',
            'orphan': 'Best Flat Top Grill Recipes for Beginners'
        },
        {
            'find': 'cooking delicate foods that might burn or stick on traditional grills, such as fish, vegetables',
            'replace': 'cooking delicate foods that might burn or stick on traditional grills (master these with our <a href="https://griddleking.com/griddle-cooking-tips-essential-techniques-for-2025/">essential griddle cooking techniques</a>), such as fish, vegetables',
            'orphan': 'Griddle Cooking Tips: Essential Techniques'
        },
        {
            'find': 'choosing the right outdoor cooking equipment can be overwhelming',
            'replace': 'choosing the right outdoor cooking equipment can be overwhelming (see our <a href="https://griddleking.com/buying-your-first-grill/">guide to buying your first grill</a>)',
            'orphan': 'Buying Your First Grill Guide'
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
            'post_url': 'https://griddleking.com/griddle-vs-grill-debate-solved/',
            'post_authority': '12 backlinks',
            'links_injected': len(changes_made),
            'orphans_rescued': changes_made,
            'timestamp': datetime.now().isoformat()
        }
        
        print("✅ POST UPDATED SUCCESSFULLY!")
        print(f"\n📊 Rescued {len(changes_made)} orphans from high-authority post:")
        for orphan in changes_made:
            print(f"  - {orphan}")
        
        # Save log
        with open('data/link_injection_log_batch3.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        return result
    else:
        print("\n⚠️  No matches found - content may have changed")
        return {'success': False, 'message': 'No matches found'}

if __name__ == '__main__':
    result = inject_links()
    print("\n" + "="*80)
    print(json.dumps(result, indent=2))
