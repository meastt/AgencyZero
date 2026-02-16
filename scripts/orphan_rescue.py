#!/usr/bin/env python3
"""
Orphan Rescue: Strategic Internal Link Distribution
Analyzes high-authority posts and injects contextual links to orphaned content.
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

class OrphanRescue:
    def __init__(self):
        self.base_url = f"{WP_URL}/wp-json/wp/v2"
        self.auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASS)
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Load orphan and authority data from robust candidate paths.
        candidates = [
            os.path.join(self.root_dir, "seo_kickstart_results.json"),
            os.path.join(self.root_dir, "data", "seo_kickstart_results.json"),
        ]
        data = None
        used_path = None
        for path in candidates:
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = json.load(f)
                used_path = path
                break

        if not data:
            raise FileNotFoundError(
                "Could not find seo_kickstart_results.json in expected locations: "
                + ", ".join(candidates)
            )

        self.orphans = data.get('orphaned_posts', [])
        self.authorities = data.get('high_authority_posts', [])
        print(f"Loaded SEO snapshot from: {used_path}")
    
    def fetch_full_post(self, url):
        """Fetch complete post data including full content."""
        slug = url.rstrip('/').split('/')[-1]
        api_url = f"{self.base_url}/posts?slug={slug}&_fields=id,title,content,link,slug"
        
        response = requests.get(api_url, auth=self.auth, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        posts = response.json()
        
        return posts[0] if posts else None
    
    def find_link_opportunities(self, authority_post, orphans_subset):
        """
        Analyze authority post content and match with relevant orphans.
        Returns list of injection opportunities.
        """
        content = authority_post['content']['rendered']
        opportunities = []
        
        # Keyword matching logic
        keyword_map = {
            'temperature': ['temperature', 'heat zones', 'heat control'],
            'setup': ['setup', 'installation', 'first use', 'getting started'],
            'electric': ['electric griddle', 'indoor griddle', 'plug-in'],
            'commercial': ['commercial', 'restaurant', 'professional'],
            'outdoor': ['outdoor', 'backyard', 'patio'],
            'breakfast': ['breakfast', 'pancakes', 'eggs', 'morning'],
            'recipes': ['recipe', 'cooking tips', 'techniques', 'how to cook'],
            'cleaning': ['clean', 'maintenance', 'care'],
            'comparison': ['vs', 'versus', 'comparison', 'alternative']
        }
        
        for orphan in orphans_subset:
            orphan_title = orphan['title'].lower()
            orphan_url = orphan['url']
            
            # Check which keywords match
            for category, keywords in keyword_map.items():
                for keyword in keywords:
                    if keyword in content.lower() and keyword in orphan_title:
                        opportunities.append({
                            'orphan_url': orphan_url,
                            'orphan_title': orphan['title'],
                            'match_keyword': keyword,
                            'category': category,
                            'relevance_score': 1.0
                        })
                        break
        
        return opportunities
    
    def inject_strategic_links(self, authority_url, max_links=5):
        """
        Main execution: fetch authority post, identify orphans, inject links.
        """
        print(f"\n🎯 ORPHAN RESCUE MISSION: {authority_url}")
        print("=" * 80)
        
        # Fetch authority post
        authority = self.fetch_full_post(authority_url)
        if not authority:
            return {'error': 'Authority post not found'}
        
        print(f"✅ Loaded: {authority['title']['rendered']}")
        
        # Find opportunities (limit to first 10 orphans for efficiency)
        opportunities = self.find_link_opportunities(
            authority, 
            self.orphans[:10]
        )
        
        print(f"🔍 Found {len(opportunities)} link opportunities")
        
        if not opportunities:
            print("❌ No matching orphans found for this authority post")
            return {'success': False, 'message': 'No opportunities'}
        
        # Sort by relevance and take top N
        opportunities = sorted(
            opportunities, 
            key=lambda x: x['relevance_score'], 
            reverse=True
        )[:max_links]
        
        print(f"\n📋 Top {len(opportunities)} candidates:")
        for i, opp in enumerate(opportunities, 1):
            print(f"  {i}. {opp['orphan_title']}")
            print(f"     Match: '{opp['match_keyword']}' | Category: {opp['category']}")
        
        # Manual link injection (semi-automated for safety)
        print("\n⚠️  MANUAL REVIEW REQUIRED")
        print("Copy these link insertions to WordPress editor:")
        print("-" * 80)
        
        for opp in opportunities:
            anchor_text = opp['orphan_title'].split(':')[0]  # Use first part of title
            print(f"\nKeyword context: '{opp['match_keyword']}'")
            print(f"Insert: <a href=\"{opp['orphan_url']}\">{anchor_text}</a>")
        
        return {
            'success': True,
            'authority_post': authority['title']['rendered'],
            'opportunities': opportunities,
            'action_required': 'manual_insertion'
        }

def main():
    rescue = OrphanRescue()

    if not rescue.authorities:
        result = {
            "success": False,
            "message": "No high_authority_posts available in seo_kickstart_results.json",
            "action_required": "run_seo_audit_first",
        }
        print(json.dumps(result, indent=2))
        return

    # Start with highest authority post
    top_authority = rescue.authorities[0]['url']
    
    result = rescue.inject_strategic_links(top_authority, max_links=5)
    
    print("\n" + "=" * 80)
    print("📊 MISSION SUMMARY")
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
