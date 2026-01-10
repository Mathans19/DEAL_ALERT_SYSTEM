import time
import re
import os
import sys
import random
import tempfile
import django
from decimal import Decimal
from datetime import datetime

def init_django():
    """Explicitly initialize Django settings and apps."""
    if not os.getenv('DJANGO_SETTINGS_MODULE'):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_tracking_project.settings')
    django.setup()

# Call this at the TOP level so it's ready when imported or run
init_django()

# Only setup if running standalone
if __name__ == "__main__":
    init_django()
    if not os.getenv('CI') and not os.getenv('DEBUG'):
        # Avoid redirecting stdout if we are in a web environment
        pass

def setup_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from fake_useragent import UserAgent
    from selenium_stealth import stealth
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    ua = UserAgent()
    user_agent = ua.random
    options.add_argument(f"user-agent={user_agent}")
    
    # Use Selenium Manager which is built-in to modern Selenium
    driver = webdriver.Chrome(options=options)
    
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    return driver

def scrape_amazon(driver, url):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    product_name, price = None, None
    attempts = 2
    for attempt in range(attempts):
        try:
            driver.get(url)
            # Wait for either the product title OR the common "Continue" button OR CAPTCHA
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#productTitle, .a-button-text, .a-price, body"))
            )
            
            # Handle intermediate "Continue shopping" page if it exists
            continue_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), 'Continue')] | //button[contains(text(), 'Continue')]")
            if continue_buttons:
                continue_buttons[0].click()
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "productTitle")))

            # Name
            name_selectors = [ 
                (By.ID, 'productTitle'), 
                (By.CSS_SELECTOR, '.product-title-word-break'),
                (By.CSS_SELECTOR, '#title')
            ]
            for s_type, s in name_selectors:
                elements = driver.find_elements(s_type, s)
                if elements and elements[0].text.strip():
                    product_name = elements[0].text.strip()
                    break
            
            # Price
            price_selectors = [ 
                (By.CSS_SELECTOR, '#corePrice_feature_div .a-price .a-offscreen'), # Main Buy Box
                (By.CSS_SELECTOR, 'div[data-brand-sourced-offer-display] .a-price .a-offscreen'), 
                (By.CSS_SELECTOR, '.a-price.a-text-price:not(.a-size-small) .a-offscreen'),
                (By.CSS_SELECTOR, '.a-price-whole')
            ]
            found_prices = []
            for s_type, s in price_selectors:
                elements = driver.find_elements(s_type, s)
                for el in elements:
                    p_text = el.text.strip() or el.get_attribute('innerHTML').strip()
                    if p_text:
                        # Safety check: Avoid "Unit Price" (often small font or secondary color)
                        try:
                            parent = el.find_element(By.XPATH, "./..")
                            if "a-size-small" in parent.get_attribute("class") or "a-color-secondary" in parent.get_attribute("class"):
                                continue # Skip unit prices
                        except: pass
                        found_prices.append(p_text)
            
            if found_prices:
                # Pick the lowest valid price
                cleaned_prices = [p for p in [clean_price(tp) for tp in found_prices] if p is not None]
                if cleaned_prices:
                    price = f"₹{min(cleaned_prices)}" if not any('₹' in p for p in found_prices) else found_prices[0]
            
            if not price: # Fallback Regex
                body_text = driver.find_element(By.TAG_NAME, 'body').text
                matches = re.findall(r'₹\s?[\d,]+\.\d{2}|₹\s?[\d,]+', body_text)
                if matches: price = matches[0]

            # Fallback to driver.title if name not found
            if not product_name:
                title = driver.title
                if title and "Robot Check" not in title and "Amazon.in" != title:
                    if "|" in title:
                        product_name = title.split("|")[0].strip()
                    elif "-" in title:
                        product_name = title.split("-")[0].strip()
                    else:
                        product_name = title

            if product_name:
                break # Success
        except Exception as e:
            if attempt == attempts - 1:
                print(f"Amazon Error after {attempts} attempts: {e}")
            time.sleep(2) # Wait a bit before retry

    return product_name, price

def scrape_flipkart(driver, url):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    product_name, price = None, None
    attempts = 2
    for attempt in range(attempts):
        try:
            driver.get(url)
            # Wait for any common Flipkart title or price element to confirm page load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .B_NuCI, .Nx9W0j, ._30jeq3, body"))
            )
            
            # Name
            name_selectors = [ 
                (By.CSS_SELECTOR, 'h1.CEn5rD'), 
                (By.CSS_SELECTOR, 'h1.VU-Z7G'),
                (By.CSS_SELECTOR, '.B_NuCI'), 
                (By.CSS_SELECTOR, 'h1'),
                (By.CSS_SELECTOR, 'span.B_NuCI'),
                (By.CSS_SELECTOR, 'span.yhB1nd'),
                (By.CSS_SELECTOR, 'span.LMizgS')
            ]
            for s_type, s in name_selectors:
                elements = driver.find_elements(s_type, s)
                if elements and elements[0].text.strip():
                    product_name = elements[0].text.strip()
                    break
            
            # Fallback to driver.title if still None
            if not product_name:
                title = driver.title
                if title:
                    if "|" in title:
                        product_name = title.split("|")[0].strip()
                    elif "-" in title:
                        product_name = title.split("-")[0].strip()
                    else:
                        product_name = title
            
            # Price
            price_selectors = [ 
                (By.CSS_SELECTOR, '._25b18c ._30jeq3'), # Standard
                (By.CSS_SELECTOR, '.Nx9W0j'), # Discounted
                (By.CSS_SELECTOR, '._30jeq3._16Jk6d'), 
                (By.CSS_SELECTOR, '._30jeq3'),
                (By.CSS_SELECTOR, '.hZ3P6w'),
                (By.CSS_SELECTOR, '.Nx9-bo'),
                (By.XPATH, "//div[contains(@class, '_30jeq3')]")
            ]
            found_prices = []
            for s_type, s in price_selectors:
                elements = driver.find_elements(s_type, s)
                for el in elements:
                    p_text = el.text.strip()
                    if p_text: found_prices.append(p_text)
            
            if found_prices:
                # Pick the lowest valid price
                cleaned_prices = [p for p in [clean_price(tp) for tp in found_prices] if p is not None]
                if cleaned_prices:
                    # Sort to find the lowest price
                    price = f"₹{min(cleaned_prices)}"
            
            if not price: # Fallback Regex for Flipkart
                body_text = driver.find_element(By.TAG_NAME, 'body').text
                matches = re.findall(r'₹\s?[\d,]+', body_text)
                if matches: price = matches[0]
            
            if product_name:
                break # Success
        except Exception as e:
            if attempt == attempts - 1:
                print(f"Flipkart Error after {attempts} attempts: {e}")
            time.sleep(2)
    return product_name, price

def clean_price(price_str):
    if not price_str: return None
    clean_str = re.sub(r'[^0-9.]', '', price_str.replace(",", ""))
    try:
        return Decimal(clean_str)
    except:
        return None

def send_telegram_alert(product, current_price, last_price):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return

    import requests
    # Use emoji for impact
    message = f"🎁 *PRICE DROP DETECTED!*\n\n"
    message += f"📦 *{product.name}*\n\n"
    
    if last_price:
        savings = last_price - current_price
        drop_percent = (savings / last_price) * 100
        message += f"💰 *Current Price:* ₹{current_price}\n"
        message += f"📉 *Was:* ₹{last_price}\n"
        message += f"✨ *Savings:* ₹{savings} ({drop_percent:.1f}% OFF)\n\n"
    else:
        message += f"💰 *Initial Price:* ₹{current_price}\n\n"

    message += f"🚀 [Buy Now on {product.platform}]({product.url})"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": message, 
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    requests.post(url, json=payload)

def run_scraper():
    from tracker.models import TrackedProduct, ProductPrice
    products = TrackedProduct.objects.all()
    if not products:
        print("No products to track.")
        return

    driver = setup_driver()
    try:
        for product in products:
            print(f"Scraping {product.name} on {product.platform}...")
            
            if product.platform == "Amazon":
                _, raw_price = scrape_amazon(driver, product.url)
            else:
                _, raw_price = scrape_flipkart(driver, product.url)
            
            current_price = clean_price(raw_price)
            if current_price:
                # Get last recorded price
                last_entry = ProductPrice.objects.filter(product=product).order_by("-scraped_at").first()
                last_price = last_entry.price if last_entry else None
                
                # Save new price
                ProductPrice.objects.create(product=product, price=current_price)
                
                # Alert logic
                if last_price and current_price < last_price:
                    send_telegram_alert(product, current_price, last_price)
                elif not last_price:
                    print(f"Initial price record for {product.name} saved.")
            
            # Stealth sleep between products
            time.sleep(random.uniform(5, 10))
            
    finally:
        driver.quit()

if __name__ == "__main__":
    run_scraper()
