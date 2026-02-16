#!/usr/bin/env python3
"""
Automated Internal Link Injector
Safely injects contextual internal links into WordPress posts.
"""

import os
import json
import re
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

WP_URL = os.getenv('WP_URL').rstrip('/')
WP_USERNAME = os.getenv('WP_USERNAME')
WP_APP_PASS = os.getenv('WP_APP_PASS')
REQUEST_TIMEOUT = int(os.getenv('HTTP_TIMEOUT_SECONDS', '30'))

class AutoLinkInjector:
    def __init__(self):
        self.base_url = f"{WP_URL}/wp-json/wp/v2"
        self.auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASS)
        self.injection_log = []
    
    def fetch_post(self, url):
        """Fetch complete post with raw content."""
        slug = url.rstrip('/').split('/')[-1]
        api_url = f"{self.base_url}/posts?slug={slug}"
        
        response = requests.get(api_url, auth=self.auth, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        posts = response.json()
        
        return posts[0] if posts else None
    
    def find_best_insertion_point(self, content, keyword, orphan_title):
        """
        Find the best place to insert a link based on keyword context.
        Returns (paragraph_text, replacement_text) or None.
        """
        # Split content into paragraphs
        paragraphs = re.split(r'</p>|</h[2-6]>', content)
        
        for para in paragraphs:
            para_lower = para.lower()
            
            # Check if keyword is in this paragraph
            if keyword in para_lower:
                # Avoid already linked text
                if '<a href=' in para:
                    continue
                
                # Find sentences containing the keyword
                sentences = re.split(r'[.!?]', para)
                for sentence in sentences:
                    if keyword in sentence.lower():
                        # Generate anchor text (use first part of orphan title)
                        anchor = orphan_title.split(':')[0].strip()
                        
                        # Find a noun phrase near the keyword to replace
                        # Simple heuristic: capitalize words near keyword
                        words = sentence.split()
                        for i, word in enumerate(words):
                            if keyword in word.lower():
                                # Use 2-4 words around the keyword as anchor context
                                start = max(0, i - 1)
                                end = min(len(words), i + 3)
                                context_words = words[start:end]
                                context = ' '.join(context_words)
                                
                                # Clean HTML tags if any
                                context = re.sub(r'<[^>]+>', '', context)
                                
                                return (para, context, anchor)
        
        return None
    
    def inject_link(self, post_id, content, target_url, anchor_text, context):
        """
        Inject a single link into content and update post.
        """
        # Build link HTML
        link_html = f'<a href="{target_url}">{anchor_text}</a>'
        
        # Replace first occurrence of context with linked version
        # Be conservative: only replace if exact match found
        if context in content:
            new_content = content.replace(context, link_html, 1)
            
            # Update post
            update_url = f"{self.base_url}/posts/{post_id}"
            response = requests.post(
                update_url,
                json={'content': new_content},
                auth=self.auth,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            
            return True
        
        return False
    
    def smart_inject(self, authority_url, orphan_data):
        """
        Smart injection: finds natural insertion points and adds links.
        orphan_data = [{'url': ..., 'title': ..., 'keyword': ...}, ...]
        """
        print(f"\n🚀 AUTO-INJECTING LINKS INTO: {authority_url}")
        print("=" * 80)
        
        # Fetch post
        post = self.fetch_post(authority_url)
        if not post:
            return {'error': 'Post not found'}
        
        post_id = post['id']
        content = post['content']['rendered']
        original_content = content
        
        injected_count = 0
        
        for orphan in orphan_data:
            orphan_url = orphan['url']
            orphan_title = orphan['title']
            keyword = orphan['keyword']
            
            print(f"\n🔍 Searching for: '{keyword}'")
            
            # Find insertion point
            result = self.find_best_insertion_point(content, keyword, orphan_title)
            
            if result:
                para, context, anchor = result
                print(f"   ✅ Found context: '{context[:60]}...'")
                print(f"   📝 Anchor: '{anchor}'")
                
                # Inject link
                link_html = f'<a href="{orphan_url}">{anchor}</a>'
                content = content.replace(context, link_html, 1)
                
                self.injection_log.append({
                    'orphan_url': orphan_url,
                    'orphan_title': orphan_title,
                    'keyword': keyword,
                    'anchor': anchor,
                    'success': True
                })
                
                injected_count += 1
            else:
                print(f"   ❌ No suitable context found")
                self.injection_log.append({
                    'orphan_url': orphan_url,
                    'orphan_title': orphan_title,
                    'keyword': keyword,
                    'success': False,
                    'reason': 'no_context'
                })
        
        # Update post if changes were made
        if content != original_content and injected_count > 0:
            print(f"\n🔧 Updating post with {injected_count} new links...")
            
            update_url = f"{self.base_url}/posts/{post_id}"
            response = requests.post(
                update_url,
                json={'content': content},
                auth=self.auth,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            
            print("✅ POST UPDATED SUCCESSFULLY!")
            
            return {
                'success': True,
                'post_id': post_id,
                'post_url': authority_url,
                'links_injected': injected_count,
                'log': self.injection_log
            }
        else:
            print("\n⚠️  No changes made")
            return {
                'success': False,
                'message': 'No suitable injection points or links already exist'
            }

def main():
    injector = AutoLinkInjector()
    
    # Target: Flat Top Grilling 101 (highest authority)
    authority_url = "https://griddleking.com/flat-top-grilling-101-how-to/"
    
    # Orphans to link (from previous analysis)
    orphans = [
        {
            'url': 'https://griddleking.com/griddle-temperature-control-guide-2025-master-your-heat-zones/',
            'title': 'Griddle Temperature Control Guide 2026: Master Your Heat Zones',
            'keyword': 'temperature'
        },
        {
            'url': 'https://griddleking.com/electric-griddle-setup-guide-2025-complete-installation-first-use/',
            'title': 'Electric Griddle Setup Guide 2026: Complete Installation & First Use',
            'keyword': 'setup'
        },
        {
            'url': 'https://griddleking.com/griddle-cooking-tips-essential-techniques-for-2025/',
            'title': 'Griddle Cooking Tips: Essential Techniques for 2026',
            'keyword': 'cooking tips'
        },
        {
            'url': 'https://griddleking.com/commercial-vs-residential-griddles-2025-complete-buying-guide/',
            'title': 'Commercial vs Residential Griddles 2026: Complete Buying Guide',
            'keyword': 'commercial'
        }
    ]
    
    result = injector.smart_inject(authority_url, orphans)
    
    # Save result
    timestamp = datetime.now().isoformat()
    result['timestamp'] = timestamp
    
    with open('data/link_injection_log.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print("\n" + "=" * 80)
    print("📊 INJECTION COMPLETE")
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
