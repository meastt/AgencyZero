#!/usr/bin/env python3
"""
One-time state cleanup before restart.
- Deduplicates escalations (keep 1 per unique agent+issue)
- Resets last_assessment so agents do a clean inventory-first cycle
- Clears stuck pending_plans
- Resolves stale escalations
"""

import json
import os
import sys

STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")


def atomic_write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, path)


def cleanup_commander():
    path = os.path.join(STATE_DIR, "commander.json")
    if not os.path.exists(path):
        print("No commander state found.")
        return

    with open(path, "r") as f:
        cmd = json.load(f)

    # Deduplicate escalations: keep 1 per (agent_key, first 80 chars of issue)
    escalations = cmd.get("escalations", [])
    original_count = len(escalations)
    seen = set()
    deduped = []
    for esc in escalations:
        key = (esc.get("agent_key", ""), (esc.get("issue") or "")[:80].lower())
        if key not in seen:
            seen.add(key)
            deduped.append(esc)

    # Mark all unresolved as resolved (clean slate)
    for esc in deduped:
        if not esc.get("resolved"):
            esc["resolved"] = True
            esc["resolved_at"] = "2026-02-16T00:00:00"
            esc["resolution"] = "Bulk resolved during state cleanup before restart"

    cmd["escalations"] = deduped
    cmd["pending_reviews"] = []  # Clear any stuck reviews

    atomic_write(path, cmd)
    print(f"Commander: {original_count} escalations -> {len(deduped)} (all resolved)")
    print(f"Commander: cleared pending reviews")


def cleanup_agent(agent_key):
    path = os.path.join(STATE_DIR, f"agent_{agent_key}.json")
    if not os.path.exists(path):
        print(f"  {agent_key}: no state file found")
        return

    with open(path, "r") as f:
        state = json.load(f)

    changes = []

    # Reset last_assessment so first tick does a fresh inventory-based cycle
    if state.get("last_assessment"):
        state["last_assessment"] = None
        changes.append("reset last_assessment")

    # Clear stuck pending plans
    if state.get("pending_plan"):
        plan_status = state["pending_plan"].get("status", "unknown")
        state["pending_plan"] = None
        changes.append(f"cleared pending_plan (was {plan_status})")

    # Reset status to idle
    if state.get("status") not in ("idle", None):
        old = state["status"]
        state["status"] = "idle"
        state["current_task"] = None
        changes.append(f"reset status {old} -> idle")

    # Clear force_reassess flag
    if state.get("force_reassess"):
        state["force_reassess"] = False
        state["force_reassess_reason"] = None
        changes.append("cleared force_reassess")

    # Clear error log (start fresh)
    if state.get("error_log"):
        state["error_log"] = []
        changes.append("cleared error_log")

    if changes:
        atomic_write(path, state)
        print(f"  {agent_key}: {', '.join(changes)}")
    else:
        print(f"  {agent_key}: already clean")


def main():
    print("=" * 60)
    print("STATE CLEANUP — preparing for clean restart")
    print("=" * 60)

    print("\n1. Commander state:")
    cleanup_commander()

    print("\n2. Agent states:")
    for agent_key in ["griddle", "photo", "tiger"]:
        cleanup_agent(agent_key)

    print("\nDone. Safe to restart commander_bot.py now.")
    print("First cycle will run build_inventory for each site (~2-3 min).")


if __name__ == "__main__":
    main()
