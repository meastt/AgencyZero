#!/usr/bin/env python3
"""
Re-scan for orphan posts and high-authority posts.
Generates fresh data for continued link injection campaign.
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

class OrphanScanner:
    def __init__(self):
        self.base_url = f"{WP_URL}/wp-json/wp/v2"
        self.auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASS)
        self.posts = []
        self.link_graph = {}
    
    def fetch_all_posts(self):
        """Fetch all published posts."""
        print("🔍 Fetching all posts from WordPress...")
        page = 1
        per_page = 100
        
        while True:
            api_url = f"{self.base_url}/posts?per_page={per_page}&page={page}&status=publish"
            response = requests.get(api_url, auth=self.auth, timeout=REQUEST_TIMEOUT)
            
            if response.status_code != 200:
                break
            
            batch = response.json()
            if not batch:
                break
            
            self.posts.extend(batch)
            print(f"   Loaded {len(self.posts)} posts...")
            page += 1
        
        print(f"✅ Total posts: {len(self.posts)}")
        return self.posts
    
    def build_link_graph(self):
        """Build internal link graph to identify orphans and authorities."""
        print("\n🕸️  Building link graph...")
        
        # Initialize graph
        for post in self.posts:
            post_url = post['link']
            self.link_graph[post_url] = {
                'id': post['id'],
                'title': post['title']['rendered'],
                'url': post_url,
                'inbound_links': [],
                'outbound_links': []
            }
        
        # Count links
        for post in self.posts:
            content = post['content']['rendered']
            post_url = post['link']
            
            # Find all internal links in content
            for other_url, data in self.link_graph.items():
                if other_url != post_url and other_url in content:
                    # This post links to other_url
                    self.link_graph[post_url]['outbound_links'].append(other_url)
                    self.link_graph[other_url]['inbound_links'].append(post_url)
        
        print("✅ Link graph complete")
    
    def identify_orphans_and_authorities(self):
        """Identify orphan posts (0 inbound) and high-authority posts (many inbound)."""
        orphans = []
        authorities = []
        
        for url, data in self.link_graph.items():
            inbound_count = len(data['inbound_links'])
            outbound_count = len(data['outbound_links'])
            
            if inbound_count == 0:
                orphans.append({
                    'url': url,
                    'title': data['title'],
                    'id': data['id'],
                    'outbound_links': outbound_count
                })
            
            if inbound_count >= 3:  # High-authority threshold
                authorities.append({
                    'url': url,
                    'title': data['title'],
                    'id': data['id'],
                    'inbound_links': inbound_count,
                    'outbound_links': outbound_count
                })
        
        # Sort authorities by inbound link count
        authorities = sorted(authorities, key=lambda x: x['inbound_links'], reverse=True)
        
        return orphans, authorities
    
    def save_results(self, orphans, authorities):
        """Save scan results to JSON."""
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_posts': len(self.posts),
            'orphaned_posts': orphans,
            'orphan_count': len(orphans),
            'high_authority_posts': authorities[:20],  # Top 20
            'authority_count': len(authorities)
        }
        
        output_file = 'data/orphan_rescan.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ Results saved to {output_file}")
        return results

def main():
    scanner = OrphanScanner()
    
    # Step 1: Fetch all posts
    scanner.fetch_all_posts()
    
    # Step 2: Build link graph
    scanner.build_link_graph()
    
    # Step 3: Identify orphans and authorities
    orphans, authorities = scanner.identify_orphans_and_authorities()
    
    print("\n" + "=" * 80)
    print(f"📊 ORPHAN ANALYSIS")
    print("=" * 80)
    print(f"🚨 Orphans (0 inbound links): {len(orphans)}")
    print(f"⭐ High-Authority Posts (3+ inbound): {len(authorities)}")
    
    # Show top 5 orphans and top 10 authorities
    print(f"\n🚨 Top 10 Orphans:")
    for i, orphan in enumerate(orphans[:10], 1):
        print(f"  {i}. {orphan['title']}")
    
    print(f"\n⭐ Top 10 Authority Posts:")
    for i, auth in enumerate(authorities[:10], 1):
        print(f"  {i}. {auth['title']} ({auth['inbound_links']} inbound)")
    
    # Step 4: Save results
    scanner.save_results(orphans, authorities)

if __name__ == '__main__':
    main()
