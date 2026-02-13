#!/usr/bin/env python3
"""
Content Audit - Find optimization opportunities
"""
import json
from datetime import datetime, timedelta

# Load posts
with open('data/wp_posts.json', 'r') as f:
    posts = json.load(f)

print(f"📝 CONTENT AUDIT: {len(posts)} posts analyzed")
print("=" * 80)

# Parse dates
now = datetime.now()
for post in posts:
    post['date_obj'] = datetime.fromisoformat(post['date'].replace('Z', '+00:00'))
    post['modified_obj'] = datetime.fromisoformat(post['modified'].replace('Z', '+00:00'))
    post['days_since_update'] = (now - post['modified_obj']).days

# Find neglected content (not updated in 6+ months)
neglected = [p for p in posts if p['days_since_update'] > 180]
neglected.sort(key=lambda x: x['days_since_update'], reverse=True)

print(f"\n🕰️  NEGLECTED CONTENT (Not updated in 6+ months): {len(neglected)}")
print("-" * 80)
for post in neglected[:15]:
    title = post['title']['rendered'].replace('&#8217;', "'").replace('&#038;', '&')
    print(f"🔴 {title}")
    print(f"   Last updated: {post['days_since_update']} days ago")
    print(f"   URL: {post['link']}\n")

# Find content updated recently (potential winners to double down on)
recent = [p for p in posts if p['days_since_update'] <= 30]
print(f"\n✅ RECENTLY UPDATED (Last 30 days): {len(recent)}")
print("-" * 80)
for post in recent[:10]:
    title = post['title']['rendered'].replace('&#8217;', "'").replace('&#038;', '&')
    print(f"🟢 {title}")
    print(f"   Updated: {post['days_since_update']} days ago\n")

# Find 2025 content that needs 2026 update
needs_year_update = []
for post in posts:
    title = post['title']['rendered']
    if '2025' in title or '2024' in title:
        needs_year_update.append(post)

print(f"\n📅 NEEDS YEAR UPDATE (2024/2025 → 2026): {len(needs_year_update)}")
print("-" * 80)
for post in needs_year_update[:10]:
    title = post['title']['rendered'].replace('&#8217;', "'").replace('&#038;', '&')
    print(f"🟡 {title}")
    print(f"   URL: {post['link']}\n")

# Summary
print("\n📊 QUICK STATS:")
print(f"Total posts: {len(posts)}")
print(f"Neglected (6+ months): {len(neglected)}")
print(f"Recently updated (30 days): {len(recent)}")
print(f"Needs year update: {len(needs_year_update)}")

# Save opportunities
output = {
    'timestamp': datetime.now().isoformat(),
    'neglected': neglected[:20],
    'recent': recent,
    'needs_year_update': needs_year_update,
    'stats': {
        'total': len(posts),
        'neglected': len(neglected),
        'recent': len(recent),
        'needs_year_update': len(needs_year_update)
    }
}

with open('data/content_opportunities.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n✅ Data saved to data/content_opportunities.json")
