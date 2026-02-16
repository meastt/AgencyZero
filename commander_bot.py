#!/usr/bin/env python3
"""
Commander SEO Bot — Autonomous Command Center
Listens for Telegram messages, routes commands to agents, uses Commander Brain
for intelligent context-aware responses. Runs agent scheduler for autonomy.

Usage:
    python3 commander_bot.py          # Start polling + scheduler
    python3 commander_bot.py --once   # Process one update and exit (testing)
"""

import os
import sys
import json
import time
import argparse
import requests
import threading
from datetime import datetime
from dotenv import load_dotenv

# Load root .env
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

# Add project root to path for imports
sys.path.insert(0, ROOT_DIR)
from agents.agent_dispatch import (
    AGENTS,
    resolve_agent,
    list_agent_capabilities,
    run_agent_script,
    send_agent_message,
)
from core.state_store import StateStore
from core.claude_client import ClaudeClient
from core.commander_brain import CommanderBrain

# ── Config ──────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
AUTHORIZED_CHAT_ID = CHAT_ID  # Only respond to the owner
AGENT_DIRECT_TELEGRAM = os.getenv("AGENT_DIRECT_TELEGRAM", "false").lower() in ("1", "true", "yes", "on")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
POLL_TIMEOUT = 30  # seconds for long-polling
MESSAGE_LOG = os.path.join(ROOT_DIR, "data", "commander_messages.jsonl")
INSTANCE_LOCK_PATH = os.path.join(ROOT_DIR, "state", "commander_bot.lock")
START_CONFIRM_TTL_SECONDS = 120

# ── Initialize Core Systems ────────────────────────────────────────────────
state_store = StateStore(os.path.join(ROOT_DIR, "state"))
claude_client = ClaudeClient(ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Commander brain (scheduler wires in trigger_fn after init)
commander_brain = None
agent_brains = {}
scheduler = None
_instance_lock_acquired = False
_start_confirm_pending = {}


def relay_agent_update(agent_key, agent_name, message):
    """Route agent updates into Commander chain-of-command.

    Default behavior: internal-only (timeline/state), no direct site-bot messages.
    Optional override for debugging via AGENT_DIRECT_TELEGRAM=true.
    """
    state_store.log_commander_timeline(
        "agent_update",
        f"{agent_key}: {(message or '')[:300]}",
        {"agent_key": agent_key, "agent_name": agent_name},
    )
    if AGENT_DIRECT_TELEGRAM:
        agent = AGENTS.get(agent_key)
        if agent:
            send_agent_message(agent, message)


def _send_help(chat_id):
    send_message(
        "*Commander SEO Bot Online*\n\n"
        "I'm the director of OpenClaw SEO. Here's what I can do:\n\n"
        "*Site Commands:*\n"
        "/griddle -- Griddle King operations\n"
        "/photo -- Photo Tips Guy operations\n"
        "/tiger -- Tiger Tribe operations\n\n"
        "*Fleet Commands:*\n"
        "/status -- Live fleet status\n"
        "/mission -- Current mission overview\n"
        "/portfolio -- Portfolio allocation + KPI deltas\n"
        "/audit `[site]` -- Run SEO audit\n"
        "/keywords `[site]` -- Run keyword research\n\n"
        "*Safety:*\n"
        "/start -- Request immediate full reassessment (confirmation required)\n"
        "/start confirm -- Confirm and trigger all agents now\n\n"
        "Or just type naturally -- I understand context and remember your conversation.",
        chat_id,
    )


def _trigger_all_agents_now():
    """Trigger immediate forced reassessment across all agents."""
    for key in AGENTS.keys():
        state_store.request_reassess(key, reason="manual /start confirm")
        if scheduler:
            scheduler.trigger_now(key)
        elif commander_brain:
            commander_brain._trigger(key, force_reassess=True)  # noqa: SLF001
    state_store.log_commander_timeline(
        "manual_start_confirm",
        "Manual /start confirm triggered all agents for forced reassessment.",
        {"agents": list(AGENTS.keys())},
    )


def _acquire_instance_lock():
    """Prevent multiple local commander instances from running at once."""
    global _instance_lock_acquired
    os.makedirs(os.path.dirname(INSTANCE_LOCK_PATH), exist_ok=True)
    pid = os.getpid()

    if os.path.exists(INSTANCE_LOCK_PATH):
        try:
            with open(INSTANCE_LOCK_PATH, "r") as f:
                existing_pid = int((f.read() or "").strip())
            if existing_pid and existing_pid != pid:
                try:
                    os.kill(existing_pid, 0)
                    print(
                        f"Another commander_bot.py instance is already running (pid={existing_pid}). "
                        "Stop it before starting a new poller."
                    )
                    return False
                except OSError:
                    pass  # stale pid file
        except (OSError, ValueError):
            pass

    try:
        with open(INSTANCE_LOCK_PATH, "w") as f:
            f.write(str(pid))
        _instance_lock_acquired = True
        return True
    except OSError as e:
        print(f"Could not create instance lock: {e}")
        return False


def _release_instance_lock():
    """Release local commander instance lock if owned by this process."""
    global _instance_lock_acquired
    if not _instance_lock_acquired:
        return

    try:
        if os.path.exists(INSTANCE_LOCK_PATH):
            with open(INSTANCE_LOCK_PATH, "r") as f:
                owner = int((f.read() or "").strip() or "0")
            if owner == os.getpid():
                os.unlink(INSTANCE_LOCK_PATH)
    except (OSError, ValueError):
        pass
    finally:
        _instance_lock_acquired = False


def _init_brain():
    """Initialize Commander brain. Called after scheduler is available."""
    global commander_brain
    if not claude_client:
        return

    trigger_fn = None
    set_interval_fn = None
    if scheduler:
        trigger_fn = scheduler.trigger_now
        set_interval_fn = scheduler.set_interval

    commander_brain = CommanderBrain(
        state_store=state_store,
        claude_client=claude_client,
        agent_keys=list(AGENTS.keys()),
        trigger_fn=trigger_fn,
        set_interval_fn=set_interval_fn,
    )


# ── Message Logging ────────────────────────────────────────────────────────
def log_message(direction, chat_id, text, username=None, metadata=None):
    """Append a message to the JSONL log file."""
    os.makedirs(os.path.dirname(MESSAGE_LOG), exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(),
        "dir": direction,  # "in" or "out"
        "chat_id": chat_id,
        "text": text[:2000],
    }
    if username:
        entry["user"] = username
    if metadata:
        entry.update(metadata)
    try:
        with open(MESSAGE_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# ── Telegram Helpers ────────────────────────────────────────────────────────
def send_message(text, chat_id=None, parse_mode="Markdown"):
    """Send a message via the Commander bot."""
    cid = chat_id or CHAT_ID
    # Truncate to Telegram's 4096 char limit
    if len(text) > 4000:
        text = text[:3997] + "..."
    log_message("out", cid, text)
    payload = {"chat_id": cid, "text": text, "parse_mode": parse_mode}
    try:
        resp = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
        if not resp.ok:
            # Markdown parse often fails on Claude output (** vs *) — send as plain text
            plain = {"chat_id": cid, "text": text}
            requests.post(f"{TELEGRAM_API}/sendMessage", json=plain, timeout=10)
    except Exception as e:
        print(f"Send failed: {e}")


def send_typing(chat_id=None):
    """Show typing indicator."""
    cid = chat_id or CHAT_ID
    try:
        requests.post(
            f"{TELEGRAM_API}/sendChatAction",
            json={"chat_id": cid, "action": "typing"},
            timeout=5,
        )
    except Exception:
        pass


# ── Command Handlers ────────────────────────────────────────────────────────
def handle_start(chat_id, args):
    """Safety-gated full reassessment trigger."""
    arg0 = args[0].lower() if args else ""
    now = time.time()
    pending_at = _start_confirm_pending.get(chat_id)

    if arg0 in ("confirm", "yes"):
        if pending_at and now - pending_at <= START_CONFIRM_TTL_SECONDS:
            _start_confirm_pending.pop(chat_id, None)
            _trigger_all_agents_now()
            send_message(
                "Confirmed. Triggering all agents now with forced reassessment.\n\n"
                "Warning acknowledged: this can rewrite/replace in-flight plans.",
                chat_id,
            )
            return
        send_message(
            "No active `/start` confirmation window found (or it expired).\n"
            "Run `/start` first, then `/start confirm` within 2 minutes.",
            chat_id,
        )
        return

    _start_confirm_pending[chat_id] = now
    send_message(
        "⚠️ *Safety Check Required*\n\n"
        "You are about to force immediate reassessment across all agents.\n"
        "This may overwrite current pending plans and cannot be undone.\n\n"
        "If you're sure, run: `/start confirm`\n"
        "Confirmation expires in 2 minutes.\n\n"
        "Use `/help` to view commands without triggering execution.",
        chat_id,
    )


def handle_help(chat_id):
    """Show command help without triggering execution."""
    _send_help(chat_id)


def handle_status(chat_id):
    """Live status from agent state files, not static markdown."""
    send_typing(chat_id)
    if commander_brain:
        status = commander_brain.get_live_status()
    else:
        status = "*FLEET STATUS*\nBrain offline (no API key). Use slash commands."
    send_message(status, chat_id)


def handle_mission(chat_id):
    """Contextual mission response from the brain."""
    send_typing(chat_id)
    if commander_brain:
        send_message(commander_brain.get_mission_overview(), chat_id)
    else:
        send_message("*MISSION*: 3 WordPress sites. SEO domination. Revenue growth.\nUse /status for agent details.", chat_id)


def handle_portfolio(chat_id):
    """Executive portfolio view: allocation + KPI outcomes."""
    send_typing(chat_id)
    if commander_brain:
        report = commander_brain.get_portfolio_status()
        send_message(report, chat_id)
    else:
        send_message("Portfolio view unavailable: brain offline.", chat_id)


def handle_site_command(chat_id, agent_key, args):
    """Handle /griddle, /photo, /tiger with optional sub-command."""
    agent = AGENTS.get(agent_key)
    if not agent:
        send_message(f"Unknown agent: {agent_key}", chat_id)
        return

    if not args:
        # Show agent capabilities
        caps = list_agent_capabilities(agent_key)
        caps += f"\n\nUsage: `/{agent_key} audit` or `/{agent_key} keywords`"
        send_message(caps, chat_id)
        return

    task = args[0].lower()
    if task not in agent.get("scripts", {}):
        send_message(f"Unknown task `{task}` for {agent['name']}. Try: {', '.join(agent.get('scripts', {}).keys())}", chat_id)
        return

    dispatch_task(chat_id, agent_key, task)


def handle_audit(chat_id, args):
    """Handle /audit [site] -- defaults to griddle if no site given."""
    if args:
        agent_key, agent = resolve_agent(args[0])
        if not agent_key:
            send_message(f"Unknown site: `{args[0]}`. Try: griddle, photo, tiger", chat_id)
            return
    else:
        agent_key = "griddle"
    dispatch_task(chat_id, agent_key, "audit")


def handle_keywords(chat_id, args):
    """Handle /keywords [site] -- defaults to griddle if no site given."""
    if args:
        agent_key, agent = resolve_agent(args[0])
        if not agent_key:
            send_message(f"Unknown site: `{args[0]}`. Try: griddle, photo, tiger", chat_id)
            return
    else:
        agent_key = "griddle"
    dispatch_task(chat_id, agent_key, "keywords")


def dispatch_task(chat_id, agent_key, task_name):
    """Run an agent task in a background thread and report results."""
    agent = AGENTS[agent_key]
    send_message(f"Dispatching `{task_name}` to {agent['emoji']} *{agent['name']}*...", chat_id)
    send_typing(chat_id)

    # Update agent state
    state_store.set_agent_status(agent_key, "executing", task=task_name)

    def _run():
        success, output = run_agent_script(agent_key, task_name)
        if success:
            # Summarize output (last 1500 chars)
            summary = output[-1500:] if len(output) > 1500 else output
            send_message(
                f"{agent['emoji']} *{agent['name']}* -- `{task_name}` complete\n\n```\n{summary}\n```",
                chat_id,
            )
            # Update state
            state_store.complete_task(agent_key, f"{task_name} (manual dispatch)")
        else:
            send_message(output, chat_id)
            state_store.log_agent_error(agent_key, f"{task_name} failed: {output[:200]}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def handle_natural_language(chat_id, text):
    """Use Commander Brain for intelligent, context-aware responses."""
    send_typing(chat_id)

    if not commander_brain:
        send_message("Brain offline (no API key). Use slash commands instead.", chat_id)
        return

    try:
        reply, actions = commander_brain.handle_message(text)
    except Exception as e:
        print(f"Brain error: {e}")
        fallback = commander_brain.get_factual_reply_if_applicable(text)
        if fallback:
            send_message(fallback, chat_id)
        else:
            send_message(
                f"Brain error: {str(e)[:200]}. Fallback status:\n\n{commander_brain.get_live_status()}",
                chat_id,
            )
        return

    send_message(reply, chat_id)


# ── Message Router ──────────────────────────────────────────────────────────
def process_message(message):
    """Route an incoming Telegram message to the right handler."""
    chat_id = str(message.get("chat", {}).get("id", ""))
    text = message.get("text", "").strip()
    username = message.get("from", {}).get("username", "unknown")

    if not text:
        return

    # Security: only respond to authorized chat
    if AUTHORIZED_CHAT_ID and chat_id != AUTHORIZED_CHAT_ID:
        print(f"Unauthorized message from chat {chat_id} (@{username}): {text[:50]}")
        return

    print(f"@{username}: {text}")
    log_message("in", chat_id, text, username=username)

    # Parse command
    if text.startswith("/"):
        parts = text.split()
        command = parts[0].lower().split("@")[0]  # Strip @botname suffix
        args = parts[1:]

        handlers = {
            "/start": lambda: handle_start(chat_id, args),
            "/help": lambda: handle_help(chat_id),
            "/status": lambda: handle_status(chat_id),
            "/mission": lambda: handle_mission(chat_id),
            "/portfolio": lambda: handle_portfolio(chat_id),
            "/griddle": lambda: handle_site_command(chat_id, "griddle", args),
            "/photo": lambda: handle_site_command(chat_id, "photo", args),
            "/tiger": lambda: handle_site_command(chat_id, "tiger", args),
            "/audit": lambda: handle_audit(chat_id, args),
            "/keywords": lambda: handle_keywords(chat_id, args),
        }

        handler = handlers.get(command)
        if handler:
            handler()
        else:
            send_message(f"Unknown command: `{command}`\nType /start for help.", chat_id)
    else:
        # Natural language -> Commander Brain
        handle_natural_language(chat_id, text)


# ── Polling Loop ────────────────────────────────────────────────────────────
def poll_updates(once=False):
    """Long-poll Telegram for updates."""
    if not BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not set. Cannot start.")
        sys.exit(1)

    # Verify bot identity
    try:
        me = requests.get(f"{TELEGRAM_API}/getMe", timeout=10).json()
        if me.get("ok"):
            bot_info = me["result"]
            print(f"Commander Bot online: @{bot_info['username']} ({bot_info['first_name']})")
        else:
            print(f"Bot token invalid: {me}")
            sys.exit(1)
    except Exception as e:
        print(f"Cannot reach Telegram API: {e}")
        sys.exit(1)

    # Clear any pending updates on startup
    try:
        requests.get(f"{TELEGRAM_API}/getUpdates", params={"offset": -1}, timeout=10)
    except Exception:
        pass

    print(f"Listening for commands (chat_id: {AUTHORIZED_CHAT_ID})...")
    print("   Press Ctrl+C to stop.\n")

    offset = None
    while True:
        try:
            params = {"timeout": POLL_TIMEOUT, "allowed_updates": ["message"]}
            if offset:
                params["offset"] = offset

            resp = requests.get(
                f"{TELEGRAM_API}/getUpdates",
                params=params,
                timeout=POLL_TIMEOUT + 10,  # nosec B113
            )
            data = resp.json()

            if not data.get("ok"):
                print(f"Telegram error: {data}")
                if data.get("error_code") == 409:
                    print(
                        "Fatal: Telegram polling conflict (409). "
                        "Only one getUpdates poller may run per bot token. Shutting down."
                    )
                    if scheduler:
                        scheduler.stop()
                    break
                time.sleep(5)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message")
                if message:
                    try:
                        process_message(message)
                    except Exception as e:
                        print(f"Error processing message: {e}")

            if once:
                break

        except KeyboardInterrupt:
            print("\nCommander Bot shutting down.")
            if scheduler:
                scheduler.stop()
            break
        except requests.exceptions.Timeout:
            continue  # Normal for long-polling
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)


# ── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Commander SEO Bot")
    parser.add_argument("--once", action="store_true", help="Process one update and exit")
    args = parser.parse_args()

    if not _acquire_instance_lock():
        sys.exit(1)

    # Initialize systems
    print("Initializing core systems...")

    # Phase 2: Commander Brain (works immediately even without agents)
    _init_brain()
    if commander_brain:
        print("  Commander Brain: ONLINE")
    else:
        print("  Commander Brain: OFFLINE (no API key)")

    # Phase 4: Agent Brains + Scheduler (if modules available)
    try:
        from core.tool_registry import ToolRegistry
        from core.agent_brain import AgentBrain
        from core.scheduler import AgentScheduler

        # Build per-agent tool registries and brains
        agent_configs = {
            "griddle": {
                "name": "Griddle King",
                "site_url": "https://griddleking.com/",
                "niche": "outdoor cooking, griddles, BBQ",
                "prefix": "WP_GRIDDLEKING",
            },
            "photo": {
                "name": "Photo Tips Guy",
                "site_url": "https://phototipsguy.com/",
                "niche": "photography, astrophotography, telescopes",
                "prefix": "WP_PHOTOTIPSGUY_COM",
            },
            "tiger": {
                "name": "Tiger Tribe",
                "site_url": "https://tigertribe.net/",
                "niche": "wild cats, predatory wildlife, conservation",
                "prefix": "WP_TIGERTRIBE_NET",
            },
        }

        for key, cfg in agent_configs.items():
            tool_reg = ToolRegistry(ROOT_DIR, cfg["prefix"])
            # Route agent updates through Commander chain-of-command.
            telegram_fn = lambda msg, k=key, n=cfg["name"]: relay_agent_update(k, n, msg)

            brain = AgentBrain(
                agent_key=key,
                config=cfg,
                tools=tool_reg,
                state=state_store,
                claude=claude_client,
                telegram_fn=telegram_fn,
            )
            agent_brains[key] = brain

        # Start scheduler
        scheduler = AgentScheduler()
        for key, brain in agent_brains.items():
            scheduler.register_agent(key, brain, interval_minutes=15)
            brain.review_now_fn = scheduler.trigger_review_now

        # Register Commander review cycle
        if commander_brain:
            scheduler.register_review(commander_brain, interval_minutes=15)
            # Register 4-hour periodic monitoring report
            scheduler.register_report(commander_brain, send_fn=send_message, interval_hours=4)

        # Re-init brain with trigger function now that scheduler exists
        commander_brain.trigger_fn = scheduler.trigger_now
        commander_brain.set_interval_fn = scheduler.set_interval

        scheduler.start()
        print(f"  Agent Brains: {len(agent_brains)} ONLINE")
        print(f"  Scheduler: RUNNING (agents=15min, review=15min, report=4h)")

    except ImportError as e:
        print(f"  Agent system not yet available: {e}")
        print("  Running in Commander-only mode (slash commands + brain)")

    print("All systems initialized.\n")
    try:
        poll_updates(once=args.once)
    finally:
        _release_instance_lock()
