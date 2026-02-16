#!/usr/bin/env python3
"""
Update Post Meta — change a post's title and/or SEO meta description via
the WordPress REST API.  Highest-impact SEO action for CTR improvement.

The agent brain writes a small JSON instruction file before invoking this tool:
    state/pending_meta_update_{slug}.json
    {
        "updates": [
            {"post_id": 123, "new_title": "...", "new_meta_description": "..."},
            ...
        ]
    }

Usage:
    SITE_PREFIX=WP_GRIDDLEKING python3 update_post_meta.py
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
INSTRUCTION_PATH = os.path.join(STATE_DIR, f"pending_meta_update_{SLUG}.json")
CHANGELOG_PATH = os.path.join(DATA_DIR, f"meta_changelog_{SLUG}.json")
INVENTORY_PATH = os.path.join(STATE_DIR, f"inventory_{SLUG}.json")


def load_instructions():
    """Load the pending meta update instructions written by the agent brain."""
    if not os.path.exists(INSTRUCTION_PATH):
        return None
    with open(INSTRUCTION_PATH, "r") as f:
        return json.load(f)


def clear_instructions():
    """Remove the instruction file after processing."""
    if os.path.exists(INSTRUCTION_PATH):
        os.unlink(INSTRUCTION_PATH)


def update_post(post_id, data):
    """PUT to WordPress REST API to update a post."""
    url = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
    resp = requests.post(url, json=data, auth=(WP_USERNAME, WP_APP_PASS), timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def append_changelog(entry):
    """Append a change record to the changelog."""
    os.makedirs(os.path.dirname(CHANGELOG_PATH), exist_ok=True)
    log = []
    if os.path.exists(CHANGELOG_PATH):
        with open(CHANGELOG_PATH, "r") as f:
            log = json.load(f)
    log.insert(0, entry)
    log = log[:500]
    with open(CHANGELOG_PATH, "w") as f:
        json.dump(log, f, indent=2, default=str)


def update_inventory(post_id, new_title=None, new_meta=None):
    """Update the inventory entry for a post after a successful write."""
    if not os.path.exists(INVENTORY_PATH):
        return
    with open(INVENTORY_PATH, "r") as f:
        inv = json.load(f)
    entry = inv.get("posts", {}).get(str(post_id))
    if entry:
        if new_title:
            entry["title"] = new_title
        if new_meta:
            entry["meta_description"] = new_meta
        entry["last_audited_at"] = datetime.now().isoformat()
        with open(INVENTORY_PATH, "w") as f:
            json.dump(inv, f, indent=2, default=str)


def main():
    if not WP_URL or not WP_USERNAME or not WP_APP_PASS:
        print("WordPress credentials missing.")
        sys.exit(1)

    instructions = load_instructions()
    if not instructions:
        print("No pending meta updates found. Nothing to do.")
        print(json.dumps({"success": True, "updates": 0, "message": "No pending instructions"}))
        return

    updates = instructions.get("updates", [])
    if not updates:
        print("Instruction file empty.")
        clear_instructions()
        print(json.dumps({"success": True, "updates": 0, "message": "Empty instruction file"}))
        return

    results = []
    succeeded = 0
    failed = 0

    for item in updates[:20]:  # Safety cap: max 20 updates per run
        post_id = item.get("post_id")
        new_title = item.get("new_title")
        new_meta = item.get("new_meta_description")

        if not post_id:
            continue

        # Build the WordPress update payload
        data = {}
        if new_title:
            data["title"] = new_title
        # WordPress REST API doesn't natively support meta descriptions.
        # Yoast/Rank Math use custom meta fields.  We update the excerpt as
        # a universal fallback, and try the Yoast meta field if available.
        if new_meta:
            data["excerpt"] = new_meta
            data["meta"] = {"_yoast_wpseo_metadesc": new_meta}

        if not data:
            continue

        try:
            print(f"Updating post {post_id}...", end=" ")

            # Fetch current values for changelog
            current = requests.get(
                f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                auth=(WP_USERNAME, WP_APP_PASS),
                timeout=TIMEOUT,
            ).json()
            old_title = current.get("title", {}).get("rendered", "")
            old_excerpt = current.get("excerpt", {}).get("rendered", "")

            result = update_post(post_id, data)
            succeeded += 1
            print("OK")

            change = {
                "post_id": post_id,
                "url": current.get("link", ""),
                "at": datetime.now().isoformat(),
                "changes": {},
            }
            if new_title:
                change["changes"]["title"] = {"before": old_title, "after": new_title}
            if new_meta:
                change["changes"]["meta_description"] = {"before": old_excerpt[:200], "after": new_meta}

            append_changelog(change)
            update_inventory(post_id, new_title=new_title, new_meta=new_meta)
            results.append({"post_id": post_id, "status": "ok"})
            time.sleep(0.5)

        except Exception as e:
            failed += 1
            print(f"FAILED: {e}")
            results.append({"post_id": post_id, "status": "error", "error": str(e)[:200]})

    clear_instructions()

    output = {
        "success": succeeded > 0,
        "updates": succeeded,
        "failed": failed,
        "details": results,
    }
    print(f"\nMeta updates: {succeeded} succeeded, {failed} failed")
    print(json.dumps(output))


if __name__ == "__main__":
    main()
