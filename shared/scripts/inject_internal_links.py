#!/usr/bin/env python3
"""
Internal Link Injector — reads a pending instruction file written by the agent
brain and injects contextual internal links into WordPress posts.

Instruction file: state/pending_link_inject_{slug}.json
{
    "injections": [
        {
            "source_post_id": 456,
            "target_url": "https://site.com/orphan-post/",
            "anchor_text": "best griddle recipes",
            "context_hint": "sentence or phrase near where the link should go"
        },
        ...
    ]
}

Usage:
    SITE_PREFIX=WP_GRIDDLEKING python3 inject_internal_links.py
"""

import os
import sys
import re
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
INSTRUCTION_PATH = os.path.join(STATE_DIR, f"pending_link_inject_{SLUG}.json")
CHANGELOG_PATH = os.path.join(DATA_DIR, f"link_inject_changelog_{SLUG}.json")
INVENTORY_PATH = os.path.join(STATE_DIR, f"inventory_{SLUG}.json")


def get_post(post_id):
    """Fetch a post by ID."""
    url = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
    resp = requests.get(url, auth=(WP_USERNAME, WP_APP_PASS), timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def update_post_content(post_id, content):
    """Update post content via WordPress REST API."""
    url = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
    resp = requests.post(
        url,
        json={"content": content},
        auth=(WP_USERNAME, WP_APP_PASS),
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def inject_link(content, target_url, anchor_text, context_hint=""):
    """Inject an internal link into content. Returns (new_content, success)."""
    # Don't duplicate — check if target URL already linked
    if target_url in content:
        return content, False

    link_tag = f'<a href="{target_url}">{anchor_text}</a>'

    # Strategy 1: If we have a context hint, find it and inject
    if context_hint and context_hint in content:
        if anchor_text in context_hint:
            new_context = context_hint.replace(anchor_text, link_tag, 1)
            return content.replace(context_hint, new_context, 1), True

    # Strategy 2: Find the anchor text directly in content (not already linked)
    # Make sure we don't link text that's already inside an <a> tag
    pattern = re.compile(
        rf'(?<!<a[^>]*>)(?<!["\'/])\b({re.escape(anchor_text)})\b(?![^<]*</a>)',
        re.IGNORECASE,
    )
    match = pattern.search(content)
    if match:
        start, end = match.span()
        new_content = content[:start] + link_tag + content[end:]
        return new_content, True

    return content, False


def append_changelog(entry):
    """Append to changelog."""
    os.makedirs(os.path.dirname(CHANGELOG_PATH), exist_ok=True)
    log = []
    if os.path.exists(CHANGELOG_PATH):
        with open(CHANGELOG_PATH, "r") as f:
            log = json.load(f)
    log.insert(0, entry)
    log = log[:500]
    with open(CHANGELOG_PATH, "w") as f:
        json.dump(log, f, indent=2, default=str)


def update_inventory_links(source_post_id):
    """Increment the outbound link count in inventory for the source post."""
    if not os.path.exists(INVENTORY_PATH):
        return
    with open(INVENTORY_PATH, "r") as f:
        inv = json.load(f)
    entry = inv.get("posts", {}).get(str(source_post_id))
    if entry:
        entry["internal_links_out"] = entry.get("internal_links_out", 0) + 1
        entry["last_audited_at"] = datetime.now().isoformat()
        with open(INVENTORY_PATH, "w") as f:
            json.dump(inv, f, indent=2, default=str)


def main():
    if not WP_URL or not WP_USERNAME or not WP_APP_PASS:
        print("WordPress credentials missing.")
        sys.exit(1)

    if not os.path.exists(INSTRUCTION_PATH):
        print("No pending link injections found. Nothing to do.")
        print(json.dumps({"success": True, "injected": 0, "message": "No pending instructions"}))
        return

    with open(INSTRUCTION_PATH, "r") as f:
        instructions = json.load(f)

    injections = instructions.get("injections", [])
    if not injections:
        os.unlink(INSTRUCTION_PATH)
        print(json.dumps({"success": True, "injected": 0, "message": "Empty instruction file"}))
        return

    succeeded = 0
    failed = 0
    skipped = 0
    results = []

    # Group by source post to batch updates
    by_source = {}
    for inj in injections[:30]:  # Safety cap
        src = inj.get("source_post_id")
        if src:
            by_source.setdefault(src, []).append(inj)

    for source_post_id, links in by_source.items():
        try:
            post = get_post(source_post_id)
            content = post["content"]["rendered"]
            original = content
            links_added = []

            for link in links:
                target_url = link.get("target_url", "")
                anchor_text = link.get("anchor_text", "")
                context_hint = link.get("context_hint", "")

                if not target_url or not anchor_text:
                    skipped += 1
                    continue

                content, was_injected = inject_link(content, target_url, anchor_text, context_hint)
                if was_injected:
                    links_added.append({"target": target_url, "anchor": anchor_text})

            if content != original and links_added:
                update_post_content(source_post_id, content)
                succeeded += len(links_added)
                print(f"Post {source_post_id}: injected {len(links_added)} links")

                for la in links_added:
                    append_changelog({
                        "source_post_id": source_post_id,
                        "source_url": post.get("link", ""),
                        "target_url": la["target"],
                        "anchor_text": la["anchor"],
                        "at": datetime.now().isoformat(),
                    })
                    update_inventory_links(source_post_id)

                results.append({
                    "source_post_id": source_post_id,
                    "links_added": len(links_added),
                    "status": "ok",
                })
            else:
                skipped += len(links)
                results.append({
                    "source_post_id": source_post_id,
                    "links_added": 0,
                    "status": "skipped",
                    "reason": "no suitable injection points or links already exist",
                })

            time.sleep(0.5)

        except Exception as e:
            failed += len(links)
            print(f"Post {source_post_id} FAILED: {e}")
            results.append({"source_post_id": source_post_id, "status": "error", "error": str(e)[:200]})

    os.unlink(INSTRUCTION_PATH)

    output = {
        "success": succeeded > 0,
        "injected": succeeded,
        "failed": failed,
        "skipped": skipped,
        "details": results,
    }
    print(f"\nLink injection: {succeeded} injected, {skipped} skipped, {failed} failed")
    print(json.dumps(output))


if __name__ == "__main__":
    main()
