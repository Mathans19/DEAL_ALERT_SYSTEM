import time
import re
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pushbullet import Pushbullet
from decimal import Decimal
import tempfile
import django
from django.utils import timezone

# Pushbullet API key
PB_API_KEY = os.getenv('PB_API_KEY', 'default_pushbullet_api_key')

def send_push_notification(title, body):
    try:
        pb = Pushbullet(PB_API_KEY)
        pb.push_note(title, body)
    except Exception as e:
        print(f"Failed to send push: {e}")

# Redirect stdout to suppress ChromeDriverManager messages
sys.stdout = open(os.devnull, 'w')


def setup_driver():
    # Create a temporary directory for user data
    user_data_dir = tempfile.mkdtemp()
    
    options = Options()
    options.add_argument("--headless")  # Run Chrome in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--user-data-dir={user_data_dir}")  # Unique user data directory
    
    # Create the WebDriver with the specified options
    # No need for ChromeDriverManager - Selenium will handle this automatically
    driver = webdriver.Chrome(options=options)
    
    return driver


# Extract product name and price from Amazon
def scrape_amazon_product(product_url):
    driver = setup_driver()
    product_name = None
    price = None
    
    try:
        driver.get(product_url)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        name_selectors = [
            (By.ID, 'productTitle'),
            (By.CSS_SELECTOR, '.product-title-word-break'),
            (By.CSS_SELECTOR, '.a-size-large.product-title-word-break')
        ]
        
        for selector_type, selector in name_selectors:
            try:
                name_elements = driver.find_elements(selector_type, selector)
                if name_elements:
                    product_name = name_elements[0].text.strip()
                    break
            except Exception:
                continue
        
        price_selectors = [
            (By.CSS_SELECTOR, '.a-price .a-offscreen'),
            (By.CSS_SELECTOR, '.a-price-whole'),
            (By.CSS_SELECTOR, '#price_inside_buybox'),
            (By.CSS_SELECTOR, '#priceblock_ourprice'),
            (By.CSS_SELECTOR, '#priceblock_dealprice'),
            (By.CSS_SELECTOR, '#corePrice_feature_div .a-offscreen')
        ]
        
        for selector_type, selector in price_selectors:
            try:
                price_elements = driver.find_elements(selector_type, selector)
                if price_elements:
                    price = price_elements[0].text.strip()
                    if not price and selector == '.a-price .a-offscreen':
                        price = price_elements[0].get_attribute('innerHTML').strip()
                    break
            except Exception:
                continue
        
        if not price:
            body_text = driver.find_element(By.TAG_NAME, 'body').text
            price_matches = re.findall(r'₹\s?[\d,]+\.\d{2}|₹\s?[\d,]+', body_text)
            if price_matches:
                price = price_matches[0]
    
    except Exception as e:
        print(f"Error scraping Amazon: {e}")
    finally:
        driver.quit()
    
    return product_name, price

# Extract product name and price from Flipkart
def scrape_flipkart_product(product_url):
    driver = setup_driver()
    product_name = None
    price = None
    
    try:
        driver.get(product_url)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        try:
            popups = driver.find_elements(By.CSS_SELECTOR, "button._2KpZ6l._2doB4z")
            if popups:
                popups[0].click()
                time.sleep(1)
        except:
            pass
        
        name_selectors = [
            (By.CSS_SELECTOR, '.B_NuCI'),
            (By.CSS_SELECTOR, '.yhB1nd'),
            (By.CSS_SELECTOR, '.G6XhRU'),
            (By.CSS_SELECTOR, '._35KyD6'),
            (By.CSS_SELECTOR, 'h1'),
            (By.CSS_SELECTOR, '[data-testid="title"]'),
            (By.CSS_SELECTOR, '.product-title')
        ]
        
        for selector_type, selector in name_selectors:
            try:
                elements = driver.find_elements(selector_type, selector)
                if elements and elements[0].text.strip():
                    product_name = elements[0].text.strip()
                    break
            except Exception:
                continue
        
        if not product_name:
            page_title = driver.title
            if page_title and "Flipkart.com" in page_title:
                product_name = page_title.split(" - ")[0].strip()
        
        price_selectors = [
            (By.CSS_SELECTOR, '._30jeq3._16Jk6d'),
            (By.CSS_SELECTOR, '._30jeq3'),
            (By.CSS_SELECTOR, '.CEmiEU'),
            (By.CSS_SELECTOR, '._25b18c'),
            (By.CSS_SELECTOR, '[class*="price"]'),
            (By.CSS_SELECTOR, '[data-testid="price"]')
        ]
        
        for selector_type, selector in price_selectors:
            try:
                elements = driver.find_elements(selector_type, selector)
                if elements and elements[0].text.strip():
                    price = elements[0].text.strip()
                    price = re.sub(r'[^₹\d,.]', '', price)
                    break
            except Exception:
                continue
        
        if not price:
            body_text = driver.find_element(By.TAG_NAME, 'body').text
            price_matches = re.findall(r'₹\s?[\d,]+(?:\.\d{1,2})?', body_text)
            if price_matches:
                price = price_matches[0].strip()

    except Exception as e:
        print(f"Error scraping Flipkart: {e}")
    finally:
        driver.quit()
    
    return product_name, price


# --- Save scraped data to Django DB ---
def save_to_db():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_tracking_project.settings')
    django.setup()
    from tracker.models import ProductPrice

    amazon_url = "https://www.amazon.in/dp/B0DM28ZYKN/"
    flipkart_url = "https://www.flipkart.com/conscious-chemist-sunscreen-spf-50-pa-niacinamide-blueberry-water-resistant-no-white-cast/p/itmfd5749fa16dfb"

    amazon_name, amazon_price = scrape_amazon_product(amazon_url)
    flipkart_name, flipkart_price = scrape_flipkart_product(flipkart_url)

    def clean_price(price_str):
        return Decimal(price_str.replace("₹", "").replace("Γé╣", "").replace(",", "").strip())

    # Amazon Logic
    if amazon_name and amazon_price:
        last_amazon = ProductPrice.objects.filter(platform="Amazon").order_by("-scraped_at").first()
        current_price = clean_price(amazon_price)

        if last_amazon is None:  # If no previous data exists
            ProductPrice.objects.create(platform="Amazon", name=amazon_name, price=str(current_price), scraped_at=timezone.now())
            send_push_notification("📉 Amazon Price Drop!", f"{amazon_name}\nNew Price: {amazon_price}")
        else:
            last_price = clean_price(last_amazon.price)
            if current_price < last_price:  # Only if new price is lower
                ProductPrice.objects.create(platform="Amazon", name=amazon_name, price=str(current_price), scraped_at=timezone.now())
                send_push_notification("📉 Amazon Price Drop!", f"{amazon_name}\nNew Price: {amazon_price}")

    # Flipkart Logic
    if flipkart_name and flipkart_price:
        last_flipkart = ProductPrice.objects.filter(platform="Flipkart").order_by("-scraped_at").first()
        current_price = clean_price(flipkart_price)

        if last_flipkart is None:  # If no previous data exists
            ProductPrice.objects.create(platform="Flipkart", name=flipkart_name, price=str(current_price), scraped_at=timezone.now())
            send_push_notification("📉 Flipkart Price Drop!", f"{flipkart_name}\nNew Price: {flipkart_price}")
        else:
            last_price = clean_price(last_flipkart.price)
            if current_price < last_price:  # Only if new price is lower
                ProductPrice.objects.create(platform="Flipkart", name=flipkart_name, price=str(current_price), scraped_at=timezone.now())
                send_push_notification("📉 Flipkart Price Drop!", f"{flipkart_name}\nNew Price: {flipkart_price}")

# To run the scraper
if __name__ == "__main__":
    save_to_db()
