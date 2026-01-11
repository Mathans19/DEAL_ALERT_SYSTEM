
import os
import sys
import telebot
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_tracking_project.settings')

import django
django.setup()

def set_webhook():
    load_dotenv()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env file.")
        return

    bot = telebot.TeleBot(token)

    print("\n--- 🔗 Telegram Webhook Setup for Vercel ---")
    print("To make your bot work 24/7 on the cloud, we need to link it to your Vercel URL.")
    
    domain = input("\n👉 Enter your Vercel Domain (e.g., https://my-app.vercel.app): ").strip()
    
    if not domain:
        print("❌ Domain cannot be empty.")
        return
    
    # Ensure protocol
    if not domain.startswith("http"):
        domain = "https://" + domain
    
    # Clean trailing slash
    domain = domain.rstrip("/")
    
    webhook_url = f"{domain}/bot/webhook/"
    print(f"\nSetting webhook to: {webhook_url}")
    
    try:
        # success = bot.set_webhook(url=webhook_url) # Sync method sometimes hangs if network bad
        # Using explicit method usually better for debugging scripts
        success = bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        
        if success:
            print(f"✅ SUCCESS! Webhook set to: {webhook_url}")
            print("Your bot should now respond even when this computer is off.")
            
            info = bot.get_webhook_info()
            print(f"🔍 Verification: Telegram confirms webhook URL is: {info.url}")
        else:
            print("❌ Failed to set webhook. Telegram returned False.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    set_webhook()
