#!/usr/bin/env python3
"""
Site Inventory Builder — crawls all posts for a site, builds a persistent
inventory with internal link counts, affiliate link status, word counts, etc.

Supports incremental updates: after the first full crawl, subsequent runs only
fetch posts modified since the last run.

Usage:
    SITE_PREFIX=WP_GRIDDLEKING python3 build_site_inventory.py
"""

import os
import sys
import re
import json
import time
from datetime import datetime
from html import unescape

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

# ── Config ──────────────────────────────────────────────────────────────────
SITE_PREFIX = os.getenv("SITE_PREFIX", "")
if SITE_PREFIX:
    SITE_PREFIX += "_"

WP_URL = os.getenv(f"{SITE_PREFIX}URL", os.getenv("WP_URL", "")).rstrip("/")
WP_USERNAME = os.getenv(f"{SITE_PREFIX}USERNAME", os.getenv("WP_USERNAME"))
WP_APP_PASS = os.getenv(f"{SITE_PREFIX}PASSWORD", os.getenv("WP_APP_PASS"))
TIMEOUT = int(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))

ROOT_DIR = os.path.join(os.path.dirname(__file__), "../..")
STATE_DIR = os.path.join(ROOT_DIR, "state")

raw_prefix = os.getenv("SITE_PREFIX", "")
SLUG = raw_prefix.lower().replace("wp_", "").replace("_", "") if raw_prefix else "default"
INVENTORY_PATH = os.path.join(STATE_DIR, f"inventory_{SLUG}.json")


def strip_html(html):
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", "", html or "")
    return unescape(text).strip()


def count_words(html):
    """Count words in HTML content."""
    return len(strip_html(html).split())


def extract_links(html, site_domain):
    """Extract internal and external links from HTML content."""
    href_pattern = re.compile(r'href=[\'"]([^\'"]+)[\'"]', re.IGNORECASE)
    internal = []
    amazon = []
    other_affiliate = []

    for url in href_pattern.findall(html or ""):
        url_lower = url.lower()
        if site_domain in url_lower:
            internal.append(url)
        elif "amazon.com" in url_lower or "amzn.to" in url_lower:
            amazon.append(url)
        elif any(d in url_lower for d in ("impact.com", "avantlink.com", "shareasale.com")):
            other_affiliate.append(url)

    return internal, amazon, other_affiliate


def extract_meta_description(post):
    """Try to get meta description from Yoast or Rank Math meta fields."""
    meta = post.get("yoast_head_json", {})
    if meta:
        return (meta.get("description") or "")[:300]
    # Fallback: excerpt
    excerpt = strip_html(post.get("excerpt", {}).get("rendered", ""))
    return excerpt[:300]


def fetch_all_posts(wp_auth, modified_after=None):
    """Fetch published posts, optionally filtering by modified date."""
    all_posts = []
    page = 1
    params = {"per_page": 100, "page": page, "status": "publish", "orderby": "modified", "order": "desc"}
    if modified_after:
        params["modified_after"] = modified_after

    print(f"Fetching posts from {WP_URL}...", end="", flush=True)
    while True:
        params["page"] = page
        try:
            resp = requests.get(
                f"{WP_URL}/wp-json/wp/v2/posts",
                params=params,
                auth=wp_auth,
                timeout=TIMEOUT,
            )
            if resp.status_code == 400:
                break
            if resp.status_code != 200:
                print(f"\nHTTP {resp.status_code}: {resp.text[:200]}")
                break
            posts = resp.json()
            if not posts:
                break
            all_posts.extend(posts)
            print(".", end="", flush=True)
            page += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"\nFetch error: {e}")
            break

    print(f" {len(all_posts)} posts.")
    return all_posts


def build_post_entry(post, site_domain):
    """Build an inventory entry for a single post."""
    content = post.get("content", {}).get("rendered", "")
    internal, amazon, other_aff = extract_links(content, site_domain)

    return {
        "post_id": post["id"],
        "url": post.get("link", ""),
        "slug": post.get("slug", ""),
        "title": strip_html(post.get("title", {}).get("rendered", "")),
        "meta_description": extract_meta_description(post),
        "word_count": count_words(content),
        "status": post.get("status", "publish"),
        "internal_links_out": len(internal),
        "amazon_links": len(amazon),
        "other_affiliate_links": len(other_aff),
        "publish_date": post.get("date", ""),
        "last_modified": post.get("modified", ""),
        "last_audited_at": datetime.now().isoformat(),
    }


def load_inventory():
    """Load existing inventory or return empty structure."""
    if os.path.exists(INVENTORY_PATH):
        with open(INVENTORY_PATH, "r") as f:
            return json.load(f)
    return {"meta": {}, "posts": {}}


def save_inventory(inventory):
    """Atomic write of inventory file."""
    os.makedirs(os.path.dirname(INVENTORY_PATH), exist_ok=True)
    tmp = INVENTORY_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(inventory, f, indent=2, default=str)
    os.replace(tmp, INVENTORY_PATH)


def compute_summary(posts_dict):
    """Compute aggregate stats from inventory."""
    posts = list(posts_dict.values())
    total = len(posts)
    if total == 0:
        return {}

    orphans = [p for p in posts if p.get("internal_links_out", 0) == 0]
    no_amazon = [p for p in posts if p.get("amazon_links", 0) == 0]
    short = [p for p in posts if (p.get("word_count") or 0) < 500]
    no_meta = [p for p in posts if not p.get("meta_description")]

    return {
        "total_posts": total,
        "orphan_count": len(orphans),
        "posts_without_amazon_links": len(no_amazon),
        "short_posts_under_500w": len(short),
        "posts_missing_meta_description": len(no_meta),
        "avg_word_count": int(sum(p.get("word_count", 0) for p in posts) / total),
        "total_amazon_links": sum(p.get("amazon_links", 0) for p in posts),
    }


def main():
    if not WP_URL or not WP_USERNAME or not WP_APP_PASS:
        print("WordPress credentials missing. Set SITE_PREFIX or WP_URL/WP_USERNAME/WP_APP_PASS.")
        sys.exit(1)

    site_domain = WP_URL.replace("https://", "").replace("http://", "").split("/")[0]
    wp_auth = (WP_USERNAME, WP_APP_PASS)

    inventory = load_inventory()
    posts_dict = inventory.get("posts", {})
    last_full_crawl = inventory.get("meta", {}).get("last_full_crawl")

    # Decide: full crawl or incremental
    if last_full_crawl and posts_dict:
        print(f"Incremental update (last full crawl: {last_full_crawl[:16]})")
        modified_after = last_full_crawl
        wp_posts = fetch_all_posts(wp_auth, modified_after=modified_after)
    else:
        print("Full crawl (no existing inventory)")
        wp_posts = fetch_all_posts(wp_auth)

    # Build/update entries
    updated = 0
    for post in wp_posts:
        entry = build_post_entry(post, site_domain)
        posts_dict[str(post["id"])] = entry
        updated += 1

    # Compute inbound link counts across the inventory
    all_urls = {p["url"]: pid for pid, p in posts_dict.items()}
    for pid, entry in posts_dict.items():
        entry["internal_links_in"] = 0
    # Simple inbound count: for each post, check which other posts link to it
    for pid, entry in posts_dict.items():
        # We don't have the raw link URLs stored, but we have outbound counts.
        # For a full inbound map we'd need to re-parse content.
        # For now, we mark posts with 0 outbound as orphans.
        pass

    # Save
    inventory["posts"] = posts_dict
    inventory["meta"] = {
        "site": WP_URL,
        "slug": SLUG,
        "last_full_crawl": datetime.now().isoformat() if not last_full_crawl else last_full_crawl,
        "last_updated": datetime.now().isoformat(),
        "posts_updated_this_run": updated,
        "total_posts": len(posts_dict),
    }
    # If this was a full crawl, update last_full_crawl
    if not last_full_crawl or not inventory.get("posts"):
        inventory["meta"]["last_full_crawl"] = datetime.now().isoformat()

    summary = compute_summary(posts_dict)
    inventory["summary"] = summary

    save_inventory(inventory)

    # Print summary for agent brain to consume
    print(f"\nInventory saved to {INVENTORY_PATH}")
    print(f"Total posts: {summary.get('total_posts', 0)}")
    print(f"Orphans (0 outbound links): {summary.get('orphan_count', 0)}")
    print(f"Missing meta description: {summary.get('posts_missing_meta_description', 0)}")
    print(f"Posts without Amazon links: {summary.get('posts_without_amazon_links', 0)}")
    print(f"Short posts (<500 words): {summary.get('short_posts_under_500w', 0)}")
    print(f"Average word count: {summary.get('avg_word_count', 0)}")

    # Also write summary as JSON to stdout for ToolRegistry
    result = {
        "success": True,
        "inventory_path": INVENTORY_PATH,
        "updated": updated,
        "summary": summary,
    }
    print(f"\n{json.dumps(result)}")


if __name__ == "__main__":
    main()
