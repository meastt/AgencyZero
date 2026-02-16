import os
import time
import requests
from dotenv import load_dotenv

# Load root .env
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

def poll_messages():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN missing")
        return

    print(f"🤖 Listening for messages on @TIGERTRIBE_SEO_BOT (Token ends in ...{token[-5:]})")
    print("👉 Please send a message to the bot now...")

    offset = None
    
    # Poll for 30 seconds
    end_time = time.time() + 30
    
    while time.time() < end_time:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            params = {'timeout': 5}
            if offset:
                params['offset'] = offset
                
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('ok'):
                result = data['result']
                if result:
                    for update in result:
                        update_id = update['update_id']
                        message = update.get('message', {})
                        text = message.get('text', '(no text)')
                        user = message.get('from', {}).get('username', 'Unknown')
                        print(f"✅ RECEIVED MESSAGE from @{user}: {text}")
                        offset = update_id + 1
                        return # We found one, test passed
            else:
                print(f"❌ Telegram Error: {data}")
                
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            
        time.sleep(1)
    
    print("⏳ No messages received in 30 seconds.")

if __name__ == "__main__":
    poll_messages()
