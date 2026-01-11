import os
import django

# Setup Django before importing bot_logic so load_dotenv() is called
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_tracking_project.settings')
django.setup()

from tracker.bot_logic import bot

if __name__ == "__main__":
    print("Starting Telegram Bot listener (Polling)...")
    print("Press Ctrl+C to stop.")
    try:
        # Remove webhook to avoid conflict if it was set on Vercel
        bot.remove_webhook()
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot error: {e}")
