import os
import requests
from dotenv import load_dotenv

# Load root .env
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

def get_bot_identity():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ TELEGAM_BOT_TOKEN not found in .env")
        return

    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('ok'):
            user = data['result']
            print(f"✅ MAIN BOT IDENTITY CONFIRMED")
            print(f"Name: {user.get('first_name')}")
            print(f"Username: @{user.get('username')}")
            print(f"Link: https://t.me/{user.get('username')}")
        else:
            print(f"❌ Telegram API Error: {data.get('description')}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    get_bot_identity()
