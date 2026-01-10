import os
import django
from tracker.bot_logic import bot

if __name__ == "__main__":
    print("Starting Telegram Bot listener (Polling)...")
    print("Press Ctrl+C to stop.")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot error: {e}")
