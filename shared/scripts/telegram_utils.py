#!/usr/bin/env python3
"""
Shared Telegram alerting utility.
All SEO scripts import send_telegram_alert from here — single source of truth.
"""
import os
import requests
from dotenv import load_dotenv

# Load root .env when run directly or imported
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

# Default to Griddle King values if not specified
DEFAULT_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DEFAULT_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_alert(message):
    """
    Sends a message to Telegram.
    Uses SITE_PREFIX to find specific bot/chat creds, falls back to default.
    Example: PHOTO_TELEGRAM_BOT_TOKEN

    When SUPPRESS_TELEGRAM_ALERTS=1 (set by ToolRegistry), alerts are printed
    to stdout only — the Commander chain of command handles outward messaging.
    """
    if os.getenv('SUPPRESS_TELEGRAM_ALERTS', '') in ('1', 'true', 'yes'):
        print(f"[suppressed alert] {message}")
        return

    site_prefix = os.getenv('SITE_PREFIX', '')
    if site_prefix:
        site_prefix += '_'
    
    bot_token = os.getenv(f'{site_prefix}TELEGRAM_BOT_TOKEN', DEFAULT_BOT_TOKEN)
    chat_id = os.getenv(f'{site_prefix}TELEGRAM_CHAT_ID', DEFAULT_CHAT_ID)

    if not bot_token or not chat_id:
        print(f"⚠️ Telegram config missing for {site_prefix} (Token: {bool(bot_token)}, Chat: {bool(chat_id)})")
        print(f"ALERT: {message}")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        # response.raise_for_status() # Optional: suppress noisy failures
    except Exception as e:
        print(f"⚠️ Failed to send Telegram alert: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
        send_telegram_alert(msg)
    else:
        send_telegram_alert("🔔 *System Test*: Telegram alert utility is functional.")
