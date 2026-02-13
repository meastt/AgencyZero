#!/usr/bin/env python3
"""
Keyword Opportunity Research for Griddle King
Analyzes competitor keywords and page 2 opportunities
"""

import os
import requests
import json
import time
from datetime import datetime

BRAVE_API_KEY = os.getenv('BRAVE_SEARCH_API_KEY')
SITE_URL = 'griddleking.com'

# Top competitors in griddle/grill niche
COMPETITORS = [
    'blackstonegriddles.com',
    'seriouseats.com',
    'thespruceeats.com',
    'foodandwine.com',
    'bonappetit.com'
]

# Target keywords for griddle niche
TARGET_KEYWORDS = [
    'best flat top grill',
    'blackstone griddle recipes',
    'how to season a griddle',
    'outdoor griddle reviews',
    'flat top grill vs griddle',
    'commercial griddle buying guide',
    'griddle cleaning tips',
    'best griddle for camping',
    'electric vs gas griddle',
    'griddle breakfast recipes'
]

print("🔍 KEYWORD OPPORTUNITY ANALYSIS")
print("=" * 60)

keyword_opportunities = []

for keyword in TARGET_KEYWORDS:
    print(f"\nAnalyzing: {keyword}")
    
    # Search using Brave API
    headers = {
        'Accept': 'application/json',
        'X-Subscription-Token': BRAVE_API_KEY
    }
    
    params = {
        'q': keyword,
        'count': 20
    }
    
    try:
        response = requests.get(
            'https://api.search.brave.com/res/v1/web/search',
            headers=headers,
            params=params
        )
        
        if response.status_code != 200:
            print(f"   ⚠️  Error: {response.status_code}")
            continue
            
        data = response.json()
        results = data.get('web', {}).get('results', [])
        
        # Find Griddle King position
        griddle_king_pos = None
        competitors_in_top10 = []
        
        for idx, result in enumerate(results[:20], 1):
            url = result.get('url', '')
            
            if SITE_URL in url:
                griddle_king_pos = idx
                
            # Check competitor positions
            for comp in COMPETITORS:
                if comp in url and idx <= 10:
                    competitors_in_top10.append({
                        'domain': comp,
                        'position': idx,
                        'url': url,
                        'title': result.get('title', '')
                    })
        
        # Page 2 opportunity (position 11-20)
        if griddle_king_pos and 11 <= griddle_king_pos <= 20:
            keyword_opportunities.append({
                'keyword': keyword,
                'current_position': griddle_king_pos,
                'competitors_top10': len(competitors_in_top10),
                'opportunity_score': (20 - griddle_king_pos) + len(competitors_in_top10)
            })
            print(f"   🎯 Page 2 opportunity! Position: {griddle_king_pos}")
        elif griddle_king_pos:
            print(f"   ✅ Position: {griddle_king_pos}")
        else:
            print(f"   ⚠️  Not in top 20")
        
        print(f"   Competitors in top 10: {len(competitors_in_top10)}")
        
        time.sleep(1)  # Rate limiting
        
    except Exception as e:
        print(f"   ⚠️  Error: {str(e)}")

# Sort by opportunity score
keyword_opportunities.sort(key=lambda x: x['opportunity_score'], reverse=True)

print("\n" + "=" * 60)
print("📊 TOP PAGE 2 OPPORTUNITIES:")
print("=" * 60)

for i, opp in enumerate(keyword_opportunities[:10], 1):
    print(f"{i}. {opp['keyword']}")
    print(f"   Position: {opp['current_position']} | Score: {opp['opportunity_score']}")

# Save results
results = {
    'generated_at': datetime.now().isoformat(),
    'keyword_opportunities': keyword_opportunities,
    'total_page2_keywords': len(keyword_opportunities)
}

with open('keyword_opportunities.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n✅ Results saved to keyword_opportunities.json")
