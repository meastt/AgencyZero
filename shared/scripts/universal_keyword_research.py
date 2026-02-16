#!/usr/bin/env python3
"""
Keyword Opportunity Research for Griddle King
Analyzes competitor keywords and page 2 opportunities
"""

import os
import sys
import requests
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load root .env

# Load root .env
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

from telegram_utils import send_telegram_alert


# Configuration
# Usage: SITE_PREFIX=PHOTO python3 universal_keyword_research.py

SITE_PREFIX = os.getenv('SITE_PREFIX', '')
if SITE_PREFIX:
    SITE_PREFIX += '_'

BRAVE_API_KEY = os.getenv('BRAVE_SEARCH_API_KEY')
SITE_URL = os.getenv(f'{SITE_PREFIX}GSC_SITE_URL', 'griddleking.com').replace('https://', '').replace('/', '')
REQUEST_TIMEOUT = int(os.getenv('HTTP_TIMEOUT_SECONDS', '30'))

# Niche-Specific Config Loader
# Expected format in env: WP_PHOTOTIPSGUY_COM_COMPETITORS="site A,site B,site C"
# Expected format in env: WP_PHOTOTIPSGUY_COM_TARGET_KEYWORDS="keyword A,keyword B,keyword C"

# Per-site defaults — each site gets its own niche keywords and competitors.
NICHE_DEFAULTS = {
    "WP_GRIDDLEKING_": {
        "competitors": [
            'blackstonegriddles.com', 'seriouseats.com', 'thespruceeats.com',
            'foodandwine.com', 'bonappetit.com', 'theflattopking.com',
        ],
        "keywords": [
            'best flat top grill', 'blackstone griddle recipes',
            'how to season a griddle', 'outdoor griddle reviews',
            'commercial griddle buying guide',
        ],
    },
    "WP_PHOTOTIPSGUY_COM_": {
        "competitors": [
            'digital-photography-school.com', 'petapixel.com',
            'photographylife.com', 'bhphotovideo.com', 'dpreview.com',
        ],
        "keywords": [
            'best beginner camera', 'astrophotography for beginners',
            'best smart telescope', 'night sky photography tips',
            'telescope vs camera for astrophotography',
        ],
    },
    "WP_TIGERTRIBE_NET_": {
        "competitors": [
            'worldwildlife.org', 'nationalgeographic.com',
            'defenders.org', 'panthera.org', 'bigcatrescue.org',
        ],
        "keywords": [
            'biggest wild cats', 'tiger conservation efforts',
            'types of wild cats', 'endangered big cats',
            'wild cat species list',
        ],
    },
}

# Resolve defaults for the current site prefix
niche = NICHE_DEFAULTS.get(SITE_PREFIX, {})
DEFAULT_COMPETITORS = niche.get("competitors", [])
DEFAULT_KEYWORDS = niche.get("keywords", [])

# Load from ENV or fall back to per-site defaults
competitors_env = os.getenv(f'{SITE_PREFIX}COMPETITORS')
COMPETITORS = competitors_env.split(',') if competitors_env else DEFAULT_COMPETITORS

keywords_env = os.getenv(f'{SITE_PREFIX}TARGET_KEYWORDS')
TARGET_KEYWORDS = keywords_env.split(',') if keywords_env else DEFAULT_KEYWORDS

if not TARGET_KEYWORDS:
    print(f"⚠️  No keywords configured for prefix '{SITE_PREFIX}'. Exiting.")
    exit(1)

print(f"🚀 UNIVERSAL KEYWORD RESEARCH - TARGET: {SITE_URL}")
print(f"📡 CFG PREFIX: {SITE_PREFIX if SITE_PREFIX else 'DEFAULT (Griddle King)'}")
print(f"⚔️  COMPETITORS: {len(COMPETITORS)}")
print(f"🎯 KEYWORDS: {len(TARGET_KEYWORDS)}")


# Caching Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(SCRIPT_DIR, 'data/keyword_cache.json')
STRATEGY_FILE = os.path.join(SCRIPT_DIR, 'data/market_analysis.json')
CACHE_EXPIRY_DAYS = 7

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

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
cache = load_cache()
now = datetime.now()

for keyword in TARGET_KEYWORDS:
    # Check cache first
    if keyword in cache:
        cache_entry = cache[keyword]
        cache_date = datetime.fromisoformat(cache_entry['timestamp'])
        if (now - cache_date).days < CACHE_EXPIRY_DAYS:
            print(f"\nUsing cached data for: {keyword}")
            keyword_opportunities.append(cache_entry['opportunity'])
            continue

    print(f"\nAnalyzing (API): {keyword}")

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
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 429:
            print(f"   ⚠️  Rate limited. Skipping remaining keywords.")
            break

        if response.status_code != 200:
            print(f"   ⚠️  Error: {response.status_code}")
            if not api_failure_reported:
                api_failure_reported = True
                msg = (f"🚨 *BRAVE SEARCH API FAILURE*\n"
                       f"• Status code: `{response.status_code}`\n"
                       f"• Response: `{response.text[:200]}`\n"
                       f"• Keyword research is offline")
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
        
        opportunity = {
            'keyword': keyword,
            'current_position': griddle_king_pos,
            'competitors_top10': len(competitors_in_top10),
            'opportunity_score': (20 - (griddle_king_pos or 21)) + len(competitors_in_top10)
        }
        
        # Update cache
        cache[keyword] = {
            'timestamp': now.isoformat(),
            'opportunity': opportunity
        }
        
        keyword_opportunities.append(opportunity)
        
        if griddle_king_pos and 11 <= griddle_king_pos <= 20:
            print(f"   🎯 Page 2 opportunity! Position: {griddle_king_pos}")
        elif griddle_king_pos:
            print(f"   ✅ Position: {griddle_king_pos}")
        else:
            print(f"   ⚠️  Not in top 20")
        
        print(f"   Competitors in top 10: {len(competitors_in_top10)}")
        
        time.sleep(2)  # Conservative rate limiting
        
    except Exception as e:
        print(f"   ⚠️  Error: {str(e)}")
        if not api_failure_reported:
            api_failure_reported = True
            msg = (f"🚨 *BRAVE SEARCH API ERROR*\n"
                   f"• Exception: `{str(e)[:200]}`\n"
                   f"• Keyword research is offline")
            send_telegram_alert(msg)

# Save cache
save_cache(cache)

# Sort by opportunity score
keyword_opportunities.sort(key=lambda x: x['opportunity_score'], reverse=True)

print("\n" + "=" * 60)
print("📊 TOP PAGE 2 OPPORTUNITIES:")
print("=" * 60)

for i, opp in enumerate(keyword_opportunities[:10], 1):
    pos_str = str(opp['current_position']) if opp['current_position'] else "N/A"
    print(f"{i}. {opp['keyword']}")
    print(f"   Position: {pos_str} | Score: {opp['opportunity_score']}")

# Save results
results = {
    'generated_at': datetime.now().isoformat(),
    'keyword_opportunities': keyword_opportunities,
    'total_page2_keywords': len([o for o in keyword_opportunities if o['current_position'] and 11 <= o['current_position'] <= 20])
}

os.makedirs('data', exist_ok=True)
with open('keyword_opportunities.json', 'w') as f:
    json.dump(results, f, indent=2)

# Save strategy plan (document for agent to refer to)
strategy_data = {
    'market_analysis': results,
    'competitor_list': COMPETITORS,
    'last_deep_audit': datetime.now().isoformat(),
    'next_audit_due': (datetime.now() + timedelta(days=7)).isoformat()
}

with open(STRATEGY_FILE, 'w') as f:
    json.dump(strategy_data, f, indent=2)

print(f"\n✅ Results saved to keyword_opportunities.json and {STRATEGY_FILE}")
