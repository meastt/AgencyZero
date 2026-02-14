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

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_alert(message):
    """Send failure alert to Michael via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  TELEGRAM NOT CONFIGURED — cannot send alert!")
        print(f"ALERT: {message}")
        return
    try:
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage',
            json={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown'
            },
            timeout=10
        )
    except Exception as e:
        print(f"⚠️  Failed to send Telegram alert: {e}")

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

# Pre-flight: check Brave API key exists
if not BRAVE_API_KEY:
    msg = ("🚨 *KEYWORD RESEARCH BLOCKED*\n"
           "• `BRAVE_SEARCH_API_KEY` is not set in environment\n"
           "• Keyword research is completely offline\n"
           "• Action needed: set a valid API key")
    print(msg)
    send_telegram_alert(msg)
    exit(1)

keyword_opportunities = []
api_failure_reported = False

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
            if not api_failure_reported:
                api_failure_reported = True
                msg = (f"🚨 *BRAVE SEARCH API FAILURE*\n"
                       f"• Status code: `{response.status_code}`\n"
                       f"• Response: `{response.text[:200]}`\n"
                       f"• Keyword research is offline\n"
                       f"• Check your Brave API subscription at brave.com/search/api")
                send_telegram_alert(msg)
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
        if not api_failure_reported:
            api_failure_reported = True
            msg = (f"🚨 *BRAVE SEARCH API ERROR*\n"
                   f"• Exception: `{str(e)[:200]}`\n"
                   f"• Keyword research is offline")
            send_telegram_alert(msg)

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
