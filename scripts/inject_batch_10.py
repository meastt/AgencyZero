#!/usr/bin/env python3
"""
Batch 10: Inject links into #5 authority post (24 inbound links).
Target: How to Clean Rust Off Your Blackstone Griddle in 5 Simple Steps
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
    print("🎯 BATCH 10: HOW TO CLEAN RUST OFF BLACKSTONE (24 INBOUND LINKS)")
    print("=" * 80)
    
    # Fetch target post
    slug = "how-to-clean-rust-off-a-blackstone-griddle"
    post = fetch_post_by_slug(slug)
    
    if not post:
        print("❌ Post not found!")
        return
    
    print(f"✅ Loaded: {post['title']['rendered']}")
    print(f"   Post ID: {post['id']}")
    print(f"   URL: {post['link']}")
    
    content = post['content']['rendered']
    original_content = content
    
    # Link injection targets (cleaning/maintenance related)
    injections = [
        {
            'find': 'Blackstone griddle',
            'orphan_url': 'https://griddleking.com/master-your-blackstone-griddle-seasoning-guide-and-expert-tips/',
            'orphan_title': 'Master Your Blackstone Griddle Seasoning Guide',
            'anchor': 'comprehensive Blackstone seasoning guide'
        },
        {
            'find': 'griddle maintenance',
            'orphan_url': 'https://griddleking.com/griddle-cooking-tips-essential-techniques-for-2025/',
            'orphan_title': 'Griddle Cooking Tips: Essential Techniques',
            'anchor': 'griddle maintenance and care'
        },
        {
            'find': 'cast iron',
            'orphan_url': 'https://griddleking.com/avocado-oil-for-cast-iron-the-pros-and-cons/',
            'orphan_title': 'Avocado Oil and Cast Iron',
            'anchor': 'cast iron seasoning oils'
        },
        {
            'find': 'sticky griddle',
            'orphan_url': 'https://griddleking.com/why-is-my-blackstone-griddle-sticky-after-seasoning/',
            'orphan_title': 'Why Is My Blackstone Griddle Sticky After Seasoning?',
            'anchor': 'sticky griddle solution'
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
            'post_authority': '24 inbound links',
            'links_injected': injected_count,
            'orphans_rescued': [item['orphan_title'] for item in log if item['success']],
            'timestamp': datetime.now().isoformat()
        }
        
        with open('data/link_injection_log_batch10.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n📊 Results saved to data/link_injection_log_batch10.json")
        print(json.dumps(result, indent=2))
    else:
        print("\n⚠️  No changes made")

if __name__ == '__main__':
    main()
