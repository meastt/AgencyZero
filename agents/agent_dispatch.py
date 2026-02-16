#!/usr/bin/env python3
"""
Agent Dispatch Module
Routes commands from Commander Bot to site-specific agent scripts.
Each agent runs with its own SITE_PREFIX so it uses the correct bot token and credentials.
"""

import os
import sys
import subprocess
import requests
from dotenv import load_dotenv

# Load root .env
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, '.env'))

# ── Agent Registry ──────────────────────────────────────────────────────────
# Maps agent aliases → (SITE_PREFIX, display_name, bot_token_env, chat_id_env)
AGENTS = {
    "griddle": {
        "prefix": "WP_GRIDDLEKING",
        "name": "Griddle King",
        "emoji": "🦁",
        "site_url": "https://griddleking.com/",
        "agent_dir": os.path.join(ROOT_DIR, "agents/seo_manager"),
        "scripts": {
            "audit": "seo_kickstart.py",
            "keywords": "keyword_research.py",
            "gsc": "scripts/gsc_audit.py",
            "content": "scripts/content_audit.py",
            "techseo": "scripts/tech_seo_fixer.py",
        },
    },
    "photo": {
        "prefix": "WP_PHOTOTIPSGUY_COM",
        "name": "Photo Tips Guy",
        "emoji": "📸",
        "site_url": "https://phototipsguy.com/",
        "agent_dir": os.path.join(ROOT_DIR, "agents/photo_manager"),
        "scripts": {
            "audit": "../../shared/scripts/universal_seo_audit.py",
            "keywords": "../../shared/scripts/universal_keyword_research.py",
            "affiliate": "../../shared/scripts/affiliate_audit.py",
        },
    },
    "tiger": {
        "prefix": "WP_TIGERTRIBE_NET",
        "name": "Tiger Tribe",
        "emoji": "🐅",
        "site_url": "https://tigertribe.net/",
        "agent_dir": os.path.join(ROOT_DIR, "agents/cat_manager"),
        "scripts": {
            "audit": "../../shared/scripts/universal_seo_audit.py",
            "keywords": "../../shared/scripts/universal_keyword_research.py",
            "affiliate": "../../shared/scripts/affiliate_audit.py",
        },
    },
}

# Aliases so users can type multiple forms
AGENT_ALIASES = {
    "griddle": "griddle", "griddleking": "griddle", "gk": "griddle",
    "photo": "photo", "phototips": "photo", "ptg": "photo",
    "tiger": "tiger", "tigertribe": "tiger", "tt": "tiger",
}


def resolve_agent(name):
    """Resolve an agent alias to its registry key."""
    key = AGENT_ALIASES.get(name.lower().strip())
    if key:
        return key, AGENTS[key]
    return None, None


def get_agent_bot_token(agent):
    """Return the Telegram bot token for a specific agent."""
    prefix = agent["prefix"]
    return os.getenv(f"{prefix}_TELEGRAM_BOT_TOKEN")


def get_agent_chat_id(agent):
    """Return the Telegram chat ID for a specific agent."""
    prefix = agent["prefix"]
    return os.getenv(f"{prefix}_TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_CHAT_ID"))


def send_agent_message(agent, message):
    """Send a message via an agent's own bot token."""
    token = get_agent_bot_token(agent)
    chat_id = get_agent_chat_id(agent)
    if not token or not chat_id:
        print(f"⚠️ No Telegram creds for {agent['name']}")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.ok
    except Exception as e:
        print(f"⚠️ Agent message failed ({agent['name']}): {e}")
        return False


def run_agent_script(agent_key, task_name):
    """
    Run an agent script in a subprocess with the correct SITE_PREFIX.
    Returns (success: bool, output: str).
    """
    agent = AGENTS.get(agent_key)
    if not agent:
        return False, f"Unknown agent: {agent_key}"

    scripts = agent.get("scripts", {})
    script_file = scripts.get(task_name)
    if not script_file:
        return False, f"{agent['emoji']} *{agent['name']}*: `{task_name}` not implemented yet."

    script_path = os.path.join(agent["agent_dir"], script_file)
    if not os.path.exists(script_path):
        return False, f"{agent['emoji']} *{agent['name']}*: Script not found at `{script_file}`"

    # Run with SITE_PREFIX so telegram_utils routes to the right bot
    env = os.environ.copy()
    env["SITE_PREFIX"] = agent["prefix"]

    # Add shared/scripts to PYTHONPATH so agent scripts can find telegram_utils
    shared_scripts = os.path.join(ROOT_DIR, "shared", "scripts")
    existing_pypath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{shared_scripts}:{existing_pypath}" if existing_pypath else shared_scripts

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            env=env,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min max
            cwd=agent["agent_dir"],
        )
        output = result.stdout[-2000:] if result.stdout else ""
        if result.returncode != 0:
            err = result.stderr[-500:] if result.stderr else "unknown error"
            return False, f"{agent['emoji']} *{agent['name']}* `{task_name}` failed:\n```\n{err}\n```"
        return True, output
    except subprocess.TimeoutExpired:
        return False, f"{agent['emoji']} *{agent['name']}* `{task_name}` timed out (5 min limit)."
    except Exception as e:
        return False, f"{agent['emoji']} *{agent['name']}* error: `{str(e)[:300]}`"


def get_fleet_status():
    """Build a quick fleet status message by reading strategic plans."""
    lines = ["🚀 *OPENCLAW FLEET STATUS*\n"]
    for key, agent in AGENTS.items():
        plan_path = os.path.join(agent["agent_dir"], "STRATEGIC_PLAN.md")
        if os.path.exists(plan_path):
            with open(plan_path, "r") as f:
                content = f.read(2000)
            # Extract mission line
            mission = "Active"
            for line in content.split("\n"):
                if "**Mission" in line or "Mission:" in line:
                    mission = line.strip().replace("**", "")
                    break
            lines.append(f"{agent['emoji']} *{agent['name']}*: {mission}")
        else:
            lines.append(f"{agent['emoji']} *{agent['name']}*: ⚠️ No strategic plan")
    return "\n".join(lines)


def list_agent_capabilities(agent_key):
    """List available tasks for an agent."""
    agent = AGENTS.get(agent_key)
    if not agent:
        return "Unknown agent."
    lines = [f"{agent['emoji']} *{agent['name']}* capabilities:\n"]
    for task, script in agent.get("scripts", {}).items():
        status = "✅ ready" if script else "🔜 coming soon"
        lines.append(f"  • `{task}` — {status}")
    return "\n".join(lines)
