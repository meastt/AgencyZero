#!/usr/bin/env python3
"""
WordPress Internal Link Injector
Adds contextual internal links from high-authority posts to orphaned content.
"""

import os
import sys
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

WP_URL = os.getenv('WP_URL').rstrip('/')
WP_USERNAME = os.getenv('WP_USERNAME')
WP_APP_PASS = os.getenv('WP_APP_PASS')
REQUEST_TIMEOUT = int(os.getenv('HTTP_TIMEOUT_SECONDS', '30'))

class WordPressAPI:
    def __init__(self):
        self.base_url = f"{WP_URL}/wp-json/wp/v2"
        self.auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASS)
    
    def get_post_by_slug(self, slug):
        """Fetch post by slug."""
        url = f"{self.base_url}/posts?slug={slug}"
        response = requests.get(url, auth=self.auth, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        posts = response.json()
        return posts[0] if posts else None
    
    def get_post_by_url(self, post_url):
        """Fetch post by full URL."""
        # Extract slug from URL
        slug = post_url.rstrip('/').split('/')[-1]
        return self.get_post_by_slug(slug)
    
    def update_post(self, post_id, content, title=None):
        """Update post content."""
        url = f"{self.base_url}/posts/{post_id}"
        data = {'content': content}
        if title:
            data['title'] = title
        
        response = requests.post(url, json=data, auth=self.auth, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    
    def inject_links(self, source_post_url, target_links):
        """
        Inject internal links into a source post.
        target_links: list of dicts with 'url', 'anchor_text', 'context_hint'
        """
        post = self.get_post_by_url(source_post_url)
        if not post:
            return {'error': f'Post not found: {source_post_url}'}
        
        content = post['content']['rendered']
        original_content = content
        links_added = []
        
        for link in target_links:
            url = link['url']
            anchor = link['anchor_text']
            context = link.get('context_hint', '')
            
            # Check if link already exists
            if url in content:
                continue
            
            # Smart injection: find context and add link
            if context and context in content:
                # Replace first occurrence of context with linked version
                old_text = context
                new_text = f'<a href="{url}">{anchor}</a>'
                
                # If context contains the anchor text, replace it
                if anchor in context:
                    new_text = context.replace(anchor, new_text, 1)
                    content = content.replace(old_text, new_text, 1)
                    links_added.append({
                        'url': url,
                        'anchor': anchor,
                        'method': 'context_replace'
                    })
        
        # Update post if changes were made
        if content != original_content:
            result = self.update_post(post['id'], content)
            return {
                'success': True,
                'post_id': post['id'],
                'post_url': source_post_url,
                'links_added': links_added,
                'updated_at': result['modified']
            }
        else:
            return {
                'success': False,
                'message': 'No suitable injection points found or links already exist'
            }

def main():
    if len(sys.argv) < 2:
        print("Usage: python wp_link_injector.py <command> [args]")
        print("Commands:")
        print("  fetch <url>           - Fetch post content")
        print("  inject <source_url> <targets.json> - Inject links")
        sys.exit(1)
    
    api = WordPressAPI()
    command = sys.argv[1]
    
    if command == 'fetch':
        url = sys.argv[2]
        post = api.get_post_by_url(url)
        if post:
            print(json.dumps({
                'id': post['id'],
                'title': post['title']['rendered'],
                'slug': post['slug'],
                'content': post['content']['rendered'][:500] + '...',
                'url': post['link']
            }, indent=2))
        else:
            print(f"Post not found: {url}")
    
    elif command == 'inject':
        source_url = sys.argv[2]
        targets_file = sys.argv[3]
        
        with open(targets_file, 'r') as f:
            targets = json.load(f)
        
        result = api.inject_links(source_url, targets)
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
