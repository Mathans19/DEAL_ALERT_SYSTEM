import os
import re
import telebot
import requests
from telebot import types
from tracker.models import TrackedProduct, ProductPrice
from track_prices import scrape_amazon, scrape_flipkart, setup_driver, clean_price

token = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(token)

def scrape_lite(url):
    """A fast scraper that doesn't need Chrome. Useful for Vercel/Serverless."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # Simple regex to get title
            title_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                # Clean up Amazon/Flipkart specific title suffixes
                title = title.replace("Amazon.in: Buy ", "").replace(" : Amazon.in", "")
                title = re.split(r' \| | - ', title)[0].strip()
                return title
    except Exception as e:
        print(f"Lite scrape failed: {e}")
    return None

def extract_url(text):
    url_pattern = r'https?://[^\s]+'
    match = re.search(url_pattern, text)
    return match.group(0) if match else None

@bot.message_handler(func=lambda message: message.text.strip().lower() in ['/start', 'start', '/help', 'help'])
def send_welcome(message):
    help_text = (
        "Welcome to your Price Tracker Bot!\n\n"
        "Commands:\n"
        "/list - Show all tracked products\n"
        "/remove - Delete a product from tracking\n"
        "/help - Show this help message\n\n"
        "To start tracking a new product, simply Paste/Share the link here directly from Flipkart or Amazon."
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['list'])
@bot.message_handler(func=lambda message: message.text.strip().lower() == 'list')
def list_products(message):
    products = TrackedProduct.objects.all()
    if not products:
        bot.reply_to(message, "You are not tracking any products yet.")
        return
    
    response = "*Currently Tracked Products:*\n\n"
    for i, p in enumerate(products, 1):
        latest_price = ProductPrice.objects.filter(product=p).order_by('-scraped_at').first()
        price_str = f"₹{latest_price.price}" if latest_price else "No price yet"
        response += f"{i}. *{p.name[:50]}...*\n   Price: {price_str}\n   [Link]({p.url})\n\n"
    
    bot.send_message(message.chat.id, response, parse_mode='Markdown', disable_web_page_preview=True)

@bot.message_handler(commands=['remove', 'delete'])
@bot.message_handler(func=lambda message: message.text.strip().lower() in ['remove', 'delete'])
def remove_product_list(message):
    products = TrackedProduct.objects.all()
    if not products:
        bot.reply_to(message, "No products to remove.")
        return
    
    markup = types.InlineKeyboardMarkup()
    for p in products:
        callback_data = f"del_{p.id}"
        button = types.InlineKeyboardButton(text=f"Delete: {p.name[:30]}...", callback_data=callback_data)
        markup.add(button)
    
    bot.send_message(message.chat.id, "Select a product to stop tracking:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_delete_callback(call):
    product_id = int(call.data.split('_')[1])
    try:
        product = TrackedProduct.objects.get(id=product_id)
        name = product.name
        product.delete()
        bot.answer_callback_query(call.id, f"Removed {name}")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text=f"Removed from tracker: *{name}*", parse_mode='Markdown')
    except TrackedProduct.DoesNotExist:
        bot.answer_callback_query(call.id, "Error: Product already removed.")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text="Product not found or already deleted.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()
    url = extract_url(text)
    
    if not url:
        if text.lower() not in ['/start', 'start', '/help', 'help', '/list', 'list', '/remove', 'remove']:
            bot.reply_to(message, "I didn't find a link in your message. Please share a Flipkart or Amazon product link to start tracking!")
        return

    if "amazon" not in url.lower() and "flipkart" not in url.lower() and "amzn.in" not in url.lower() and "dl.flipkart.com" not in url.lower():
        bot.reply_to(message, "Sorry, I only support Amazon and Flipkart links.")
        return

    product, created = TrackedProduct.objects.get_or_create(url=url)
    
    if not created:
        bot.reply_to(message, f"Already Tracking!\n\nProduct: {product.name}\nPlatform: {product.platform}")
        return

    try:
        platform = "Amazon" if ("amazon" in url.lower() or "amzn.in" in url.lower()) else "Flipkart"
        product.platform = platform
        
        # Try Lite Scrape first (Fast, works on Vercel)
        lite_name = scrape_lite(url)
        if lite_name:
            product.name = lite_name
            product.save()
            bot.reply_to(message, f"Added to Tracker! (Lite Mode)\n\nProduct: {lite_name}\nPlatform: {platform}\n\n*Note: Price will be updated automatically in our next hourly scan (GitHub).*")
            return

        # Fallback to Selenium (Only works locally/GitHub)
        bot.reply_to(message, f"Checking {platform} with browser... Please wait. (Note: This may fail in Vercel/Serverless)")
        
        driver = setup_driver()
        try:
            if platform == "Amazon":
                name, price = scrape_amazon(driver, url)
            else:
                name, price = scrape_flipkart(driver, url)
            
            if name:
                product.name = name
                product.save()
                
                price_val = clean_price(price)
                if price_val:
                    ProductPrice.objects.create(product=product, price=price_val)
                
                response = f"Added to Tracker!\n\nProduct: {name}\nInitial Price: {price if price else 'N/A'}\nPlatform: {platform}"
                bot.reply_to(message, response)
            else:
                product.delete()
                bot.reply_to(message, "Could not retrieve product name. Is the link valid?")
        finally:
            driver.quit()
            
    except Exception as e:
        if product.pk: product.delete()
        print(f"Error: {e}")
        bot.reply_to(message, "An error occurred while adding the product.")
