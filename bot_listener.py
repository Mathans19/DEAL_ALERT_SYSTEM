import os
import re
import django
import telebot
from telebot import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_tracking_project.settings')
django.setup()

from tracker.models import TrackedProduct
from track_prices import scrape_amazon, scrape_flipkart, setup_driver, clean_price

# Load Bot Token
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not found in environment variables.")
    print("Please ensure your .env file contains: TELEGRAM_BOT_TOKEN=your_token_here")
    exit(1)

if ":" not in TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN is malformed (missing colon).")
    print(f"Token value starting with: {TOKEN[:5]}...")
    exit(1)

bot = telebot.TeleBot(TOKEN)

def extract_url(text):
    """Simple regex to find a URL in a message."""
    url_pattern = r'https?://[^\s]+'
    match = re.search(url_pattern, text)
    return match.group(0) if match else None

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "Welcome to your Price Tracker Bot!\n\n"
        "To start tracking a product, simply Paste/Share the link here directly from Flipkart or Amazon.\n\n"
        "I'll automatically:\n"
        "1. Identify the product name\n"
        "2. Add it to your database\n"
        "3. Start tracking its price daily!"
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = extract_url(message.text)
    
    if not url:
        return # Ignore messages without links

    if "amazon" not in url.lower() and "flipkart" not in url.lower() and "amzn.in" not in url.lower():
        bot.reply_to(message, "Sorry, I only support Amazon and Flipkart links.")
        return

    msg = bot.reply_to(message, "Analyzing link... Please wait.", parse_mode='Markdown')
    
    driver = setup_driver()
    try:
        platform = "Amazon" if ("amazon" in url.lower() or "amzn.in" in url.lower()) else "Flipkart"
        
        if platform == "Amazon":
            name, raw_price = scrape_amazon(driver, url)
        else:
            name, raw_price = scrape_flipkart(driver, url)

        if not name:
            bot.edit_message_text("Could not retrieve product name. Is the link valid?", chat_id=message.chat.id, message_id=msg.message_id)
            return

        # Clean URLs (remove trackers)
        clean_url = url.split('?')[0] if 'flipkart' in url.lower() else url

        product, created = TrackedProduct.objects.get_or_create(
            url=clean_url,
            defaults={
                'name': name,
                'platform': platform
            }
        )

        if created:
            response = f"Added to Tracker!\n\nProduct: {name}\nInitial Price: {raw_price if raw_price else 'N/A'}\nPlatform: {platform}"
        else:
            response = f"Already Tracking!\n\nProduct: {name}\nPlatform: {platform}"

        bot.edit_message_text(response, chat_id=message.chat.id, message_id=msg.message_id, parse_mode='Markdown')

    except Exception as e:
        bot.edit_message_text(f"Error adding product: {str(e)}", chat_id=message.chat.id, message_id=msg.message_id)
    finally:
        driver.quit()

if __name__ == "__main__":
    print("Bot listener is running...")
    bot.infinity_polling()
