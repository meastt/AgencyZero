#!/usr/bin/env python3
"""
Batch 12: Inject links into #7 authority post (17 inbound links).
Target: Master Your Blackstone Griddle: Comprehensive Seasoning Guide
"""

import os
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

WP_URL = os.getenv('WP_URL').rstrip('/')
WP_USERNAME = os.getenv('WP_USERNAME')
WP_APP_PASS = os.getenv('WP_APP_PASS')
REQUEST_TIMEOUT = int(os.getenv('HTTP_TIMEOUT_SECONDS', '30'))

def fetch_post_by_slug(slug):
    """Fetch post by slug."""
    api_url = f"{WP_URL}/wp-json/wp/v2/posts?slug={slug}"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASS)
    
    response = requests.get(api_url, auth=auth, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    posts = response.json()
    
    return posts[0] if posts else None

def update_post_content(post_id, new_content):
    """Update post content."""
    api_url = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASS)
    
    response = requests.post(
        api_url,
        json={'content': new_content},
        auth=auth,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()

def main():
    print("🎯 BATCH 12: MASTER YOUR BLACKSTONE GRIDDLE SEASONING (17 INBOUND LINKS)")
    print("=" * 80)
    
    # Fetch target post
    slug = "how-to-season-your-new-griddle"
    post = fetch_post_by_slug(slug)
    
    if not post:
        print("❌ Post not found!")
        return
    
    print(f"✅ Loaded: {post['title']['rendered']}")
    print(f"   Post ID: {post['id']}")
    print(f"   URL: {post['link']}")
    
    content = post['content']['rendered']
    original_content = content
    
    # Link injection targets (seasoning/care related)
    injections = [
        {
            'find': 'oil selection',
            'orphan_url': 'https://griddleking.com/choosing-right-oil-for-outdoor-griddle-seasoning/',
            'orphan_title': 'Best Griddle Seasoning Oils',
            'anchor': 'best seasoning oils'
        },
        {
            'find': 'griddle care',
            'orphan_url': 'https://griddleking.com/how-to-clean-a-flat-top-grill-or-griddle/',
            'orphan_title': 'Complete Flat Top Grill Cleaning Guide',
            'anchor': 'griddle care and maintenance'
        },
        {
            'find': 'sticky residue',
            'orphan_url': 'https://griddleking.com/why-is-my-blackstone-griddle-sticky-after-seasoning/',
            'orphan_title': 'Why Is My Blackstone Griddle Sticky?',
            'anchor': 'sticky griddle fix'
        },
        {
            'find': 'heat management',
            'orphan_url': 'https://griddleking.com/griddle-temperature-control-guide-2025-master-your-heat-zones/',
            'orphan_title': 'Griddle Temperature Control Guide',
            'anchor': 'temperature and heat control'
        }
    ]
    
    injected_count = 0
    log = []
    
    for inj in injections:
        find_phrase = inj['find']
        
        # Check if phrase exists in content
        if find_phrase.lower() in content.lower():
            # Build link
            link_html = f'<a href="{inj["orphan_url"]}">{inj["anchor"]}</a>'
            
            # Replace first occurrence (case-insensitive)
            import re
            pattern = re.compile(re.escape(find_phrase), re.IGNORECASE)
            match = pattern.search(content)
            
            if match:
                # Replace matched text with linked version
                start, end = match.span()
                content = content[:start] + link_html + content[end:]
                
                print(f"\n✅ Injected: {inj['orphan_title']}")
                print(f"   Context: '{find_phrase}'")
                
                log.append({
                    'orphan_title': inj['orphan_title'],
                    'orphan_url': inj['orphan_url'],
                    'context': find_phrase,
                    'success': True
                })
                
                injected_count += 1
            else:
                print(f"\n⚠️  Phrase found but couldn't match: {find_phrase}")
                log.append({
                    'orphan_title': inj['orphan_title'],
                    'success': False,
                    'reason': 'match_failed'
                })
        else:
            print(f"\n❌ Phrase not found: {find_phrase}")
            log.append({
                'orphan_title': inj['orphan_title'],
                'success': False,
                'reason': 'phrase_not_found'
            })
    
    # Update post if changes were made
    if content != original_content and injected_count > 0:
        print(f"\n🔧 Updating post with {injected_count} new links...")
        
        update_post_content(post['id'], content)
        
        print("✅ POST UPDATED SUCCESSFULLY!")
        
        # Save log
        result = {
            'success': True,
            'post_id': post['id'],
            'post_url': post['link'],
            'post_authority': '17 inbound links',
            'links_injected': injected_count,
            'orphans_rescued': [item['orphan_title'] for item in log if item['success']],
            'timestamp': datetime.now().isoformat()
        }
        
        with open('data/link_injection_log_batch12.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n📊 Results saved to data/link_injection_log_batch12.json")
        print(json.dumps(result, indent=2))
    else:
        print("\n⚠️  No changes made")

if __name__ == '__main__':
    main()
