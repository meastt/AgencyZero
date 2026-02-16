import os
import sys
from dotenv import load_dotenv

# Load root .env
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

# Add current directory to path so we can import telegram_utils
sys.path.append(os.path.dirname(__file__))
from telegram_utils import send_telegram_alert

def test_alerts():
    sites = [
        ('Griddle King (Default)', ''),
        ('Photo Tips Guy', 'WP_PHOTOTIPSGUY_COM'),
        ('Tiger Tribe', 'WP_TIGERTRIBE_NET')
    ]

    print("🚀 TARGETING TELEGRAM CHANNELS...")
    print("==================================================")

    for name, prefix in sites:
        print(f"\nTesting: {name}")
        # telegram_utils expects SITE_PREFIX to be set in env
        os.environ['SITE_PREFIX'] = prefix
        
        try:
            send_telegram_alert(f"🦁 *OpenClaw System Alert*\nConfiguration confirmed for: *{name}*\nStatus: *ONLINE*")
            print(f"✅ Alert sent successfully for {name}")
        except Exception as e:
            print(f"❌ Failed to send alert for {name}: {e}")

if __name__ == "__main__":
    test_alerts()
