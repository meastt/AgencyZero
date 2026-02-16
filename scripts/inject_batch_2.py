#!/usr/bin/env python3
"""
Batch 2: Improved Link Injection Strategy
Target: Blue Rhino Razor vs Blackstone (3 backlinks)
Strategy: Use semantic title matching + manual insertion guidance
"""

import os
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

WP_URL = os.getenv('WP_URL').rstrip('/')
WP_USERNAME = os.getenv('WP_USERNAME')
WP_APP_PASS = os.getenv('WP_APP_PASS')
REQUEST_TIMEOUT = int(os.getenv('HTTP_TIMEOUT_SECONDS', '30'))

class BatchInjector:
    def __init__(self):
        self.base_url = f"{WP_URL}/wp-json/wp/v2"
        self.auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASS)
    
    def fetch_post(self, url):
        slug = url.rstrip('/').split('/')[-1]
        api_url = f"{self.base_url}/posts?slug={slug}"
        response = requests.get(api_url, auth=self.auth, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        posts = response.json()
        return posts[0] if posts else None
    
    def update_post(self, post_id, content):
        update_url = f"{self.base_url}/posts/{post_id}"
        response = requests.post(
            update_url,
            json={'content': content},
            auth=self.auth,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    
    def inject_manual_links(self, authority_url, link_insertions):
        """
        Manual link injection with exact HTML snippets.
        link_insertions: list of {'find': 'text to find', 'replace': 'replacement HTML'}
        """
        print(f"🎯 Injecting links into: {authority_url}")
        
        post = self.fetch_post(authority_url)
        if not post:
            return {'error': 'Post not found'}
        
        content = post['content']['rendered']
        original = content
        changes = 0
        
        for insertion in link_insertions:
            find_text = insertion['find']
            replace_html = insertion['replace']
            
            if find_text in content:
                content = content.replace(find_text, replace_html, 1)
                changes += 1
                print(f"  ✅ Replaced: {find_text[:50]}...")
            else:
                print(f"  ❌ Not found: {find_text[:50]}...")
        
        if changes > 0:
            self.update_post(post['id'], content)
            print(f"✅ Updated with {changes} new links")
            return {
                'success': True,
                'post_id': post['id'],
                'links_added': changes
            }
        else:
            print("⚠️  No changes made")
            return {'success': False, 'message': 'No matches found'}

def main():
    injector = BatchInjector()
    
    # Target: Blue Rhino Razor vs Blackstone (3 backlinks, 18 outbound)
    authority_url = "https://griddleking.com/blue-rhino-razor-vs-blackstone-griddle/"
    
    # Strategy: Look at orphans that relate to "comparison" or "buying guide" themes
    # First, let's fetch the post to see its content
    post = injector.fetch_post(authority_url)
    
    if post:
        content = post['content']['rendered']
        
        print("\n" + "="*80)
        print("POST CONTENT ANALYSIS")
        print("="*80)
        print(f"Title: {post['title']['rendered']}")
        print(f"Word count: ~{len(content.split())}")
        print(f"\nFirst 1000 chars:")
        print(content[:1000])
        print("\n" + "="*80)
        
        # Relevant orphans based on "comparison" theme:
        orphans_to_link = [
            {
                'url': 'https://griddleking.com/commercial-vs-residential-griddles-2025-complete-buying-guide/',
                'title': 'Commercial vs Residential Griddles 2026: Complete Buying Guide',
                'reason': 'Another comparison guide - perfect thematic match'
            },
            {
                'url': 'https://griddleking.com/best-electric-outdoor-griddles-2025-complete-reviews-guide/',
                'title': 'Best Electric Outdoor Griddles 2026',
                'reason': 'Buying guide - complements comparison content'
            },
            {
                'url': 'https://griddleking.com/traeger-flatrock-2-zone-review/',
                'title': 'Traeger Flatrock 2 Zone Review',
                'reason': 'Product review - similar to comparison format'
            }
        ]
        
        print("\n📋 RECOMMENDED ORPHANS TO LINK:")
        for i, orphan in enumerate(orphans_to_link, 1):
            print(f"\n{i}. {orphan['title']}")
            print(f"   URL: {orphan['url']}")
            print(f"   Why: {orphan['reason']}")
        
        print("\n" + "="*80)
        print("⚠️  MANUAL ACTION REQUIRED")
        print("="*80)
        print("Review the post content above and manually add 2-3 contextual links.")
        print("Suggested placements:")
        print("- In introduction when discussing griddle comparisons")
        print("- In 'Alternatives' or 'Other Options' section")
        print("- In conclusion when recommending further reading")

if __name__ == '__main__':
    main()
