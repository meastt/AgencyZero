#!/usr/bin/env python3
"""
Fix Affiliate Links — reads a pending instruction file and fixes broken or
untagged Amazon affiliate links in WordPress posts.

Instruction file: state/pending_affiliate_fix_{slug}.json
{
    "fixes": [
        {
            "post_id": 123,
            "broken_url": "https://amazon.com/dp/B0XXXXX",
            "fixed_url": "https://amazon.com/dp/B0XXXXX?tag=yourtag-20",
            "action": "retag"
        },
        {
            "post_id": 456,
            "insert_after": "paragraph text or heading to place link after",
            "affiliate_url": "https://amazon.com/dp/B0YYYYY?tag=yourtag-20",
            "anchor_text": "Check price on Amazon",
            "action": "insert"
        },
        ...
    ]
}

Supported actions:
    - retag: Replace broken_url with fixed_url in the post content
    - insert: Add a new affiliate link after a context phrase

Usage:
    SITE_PREFIX=WP_GRIDDLEKING python3 fix_affiliate_links.py
"""

import os
import sys
import json
import time
from datetime import datetime

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
DATA_DIR = os.path.join(ROOT_DIR, "data")

raw_prefix = os.getenv("SITE_PREFIX", "")
SLUG = raw_prefix.lower().replace("wp_", "").replace("_", "") if raw_prefix else "default"
INSTRUCTION_PATH = os.path.join(STATE_DIR, f"pending_affiliate_fix_{SLUG}.json")
CHANGELOG_PATH = os.path.join(DATA_DIR, f"affiliate_fix_changelog_{SLUG}.json")
INVENTORY_PATH = os.path.join(STATE_DIR, f"inventory_{SLUG}.json")


def get_post(post_id):
    url = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
    resp = requests.get(url, auth=(WP_USERNAME, WP_APP_PASS), timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def update_post_content(post_id, content):
    url = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
    resp = requests.post(
        url,
        json={"content": content},
        auth=(WP_USERNAME, WP_APP_PASS),
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def apply_retag(content, broken_url, fixed_url):
    """Replace a broken affiliate URL with the fixed one."""
    if broken_url not in content:
        return content, False
    return content.replace(broken_url, fixed_url), True


def apply_insert(content, insert_after, affiliate_url, anchor_text):
    """Insert a new affiliate link after a context phrase."""
    if not insert_after or insert_after not in content:
        return content, False
    link_html = f' <a href="{affiliate_url}" rel="nofollow sponsored">{anchor_text}</a>'
    return content.replace(insert_after, insert_after + link_html, 1), True


def append_changelog(entry):
    os.makedirs(os.path.dirname(CHANGELOG_PATH), exist_ok=True)
    log = []
    if os.path.exists(CHANGELOG_PATH):
        with open(CHANGELOG_PATH, "r") as f:
            log = json.load(f)
    log.insert(0, entry)
    log = log[:500]
    with open(CHANGELOG_PATH, "w") as f:
        json.dump(log, f, indent=2, default=str)


def update_inventory_affiliate(post_id, delta=1):
    """Adjust affiliate link count in inventory."""
    if not os.path.exists(INVENTORY_PATH):
        return
    with open(INVENTORY_PATH, "r") as f:
        inv = json.load(f)
    entry = inv.get("posts", {}).get(str(post_id))
    if entry:
        entry["amazon_links"] = max(0, entry.get("amazon_links", 0) + delta)
        entry["last_audited_at"] = datetime.now().isoformat()
        with open(INVENTORY_PATH, "w") as f:
            json.dump(inv, f, indent=2, default=str)


def main():
    if not WP_URL or not WP_USERNAME or not WP_APP_PASS:
        print("WordPress credentials missing.")
        sys.exit(1)

    if not os.path.exists(INSTRUCTION_PATH):
        print("No pending affiliate fixes found. Nothing to do.")
        print(json.dumps({"success": True, "fixed": 0, "message": "No pending instructions"}))
        return

    with open(INSTRUCTION_PATH, "r") as f:
        instructions = json.load(f)

    fixes = instructions.get("fixes", [])
    if not fixes:
        os.unlink(INSTRUCTION_PATH)
        print(json.dumps({"success": True, "fixed": 0, "message": "Empty instruction file"}))
        return

    succeeded = 0
    failed = 0
    skipped = 0
    results = []

    # Group by post ID
    by_post = {}
    for fix in fixes[:30]:  # Safety cap
        pid = fix.get("post_id")
        if pid:
            by_post.setdefault(pid, []).append(fix)

    for post_id, post_fixes in by_post.items():
        try:
            post = get_post(post_id)
            content = post["content"]["rendered"]
            original = content
            changes = []

            for fix in post_fixes:
                action = fix.get("action", "retag")
                applied = False

                if action == "retag":
                    content, applied = apply_retag(
                        content,
                        fix.get("broken_url", ""),
                        fix.get("fixed_url", ""),
                    )
                elif action == "insert":
                    content, applied = apply_insert(
                        content,
                        fix.get("insert_after", ""),
                        fix.get("affiliate_url", ""),
                        fix.get("anchor_text", "Check price on Amazon"),
                    )

                if applied:
                    changes.append({"action": action, "fix": fix})
                else:
                    skipped += 1

            if content != original and changes:
                update_post_content(post_id, content)
                succeeded += len(changes)
                print(f"Post {post_id}: applied {len(changes)} affiliate fixes")

                for ch in changes:
                    append_changelog({
                        "post_id": post_id,
                        "url": post.get("link", ""),
                        "action": ch["action"],
                        "at": datetime.now().isoformat(),
                    })
                    if ch["action"] == "insert":
                        update_inventory_affiliate(post_id, delta=1)

                results.append({"post_id": post_id, "fixes_applied": len(changes), "status": "ok"})
            else:
                results.append({"post_id": post_id, "fixes_applied": 0, "status": "skipped"})

            time.sleep(0.5)

        except Exception as e:
            failed += len(post_fixes)
            print(f"Post {post_id} FAILED: {e}")
            results.append({"post_id": post_id, "status": "error", "error": str(e)[:200]})

    os.unlink(INSTRUCTION_PATH)

    output = {
        "success": succeeded > 0,
        "fixed": succeeded,
        "failed": failed,
        "skipped": skipped,
        "details": results,
    }
    print(f"\nAffiliate fixes: {succeeded} applied, {skipped} skipped, {failed} failed")
    print(json.dumps(output))


if __name__ == "__main__":
    main()
