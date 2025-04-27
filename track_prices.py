import time
import os
import sys
from pushbullet import Pushbullet
from decimal import Decimal
import django
from django.utils import timezone

# Pushbullet API key
PB_API_KEY = os.getenv('PB_API_KEY', 'default_pushbullet_api_key')

def send_push_notification(title, body):
    try:
        pb = Pushbullet(PB_API_KEY)
        pb.push_note(title, body)
        print(f"Notification sent: {title} - {body}")  # Simulate notification in logs
    except Exception as e:
        print(f"Failed to send push: {e}")


# --- Simulate Scraping Data ---
def scrape_amazon_product(product_url):
    # Simulated data for Amazon
    amazon_name = "Sample Amazon Product"
    amazon_price = "₹165"
    
    return amazon_name, amazon_price


def scrape_flipkart_product(product_url):
    # Simulated data for Flipkart
    flipkart_name = "Sample Flipkart Product"
    flipkart_price = "₹150"
    
    return flipkart_name, flipkart_price


# --- Save Scraped Data to DB (Simulated) ---
def save_to_db():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_tracking_project.settings')
    django.setup()
    from tracker.models import ProductPrice

    amazon_url = "https://www.amazon.in/dp/B0DM28ZYKN/"
    flipkart_url = "https://www.flipkart.com/conscious-chemist-sunscreen-spf-50-pa-niacinamide-blueberry-water-resistant-no-white-cast/p/itmfd5749fa16dfb"

    amazon_name, amazon_price = scrape_amazon_product(amazon_url)
    flipkart_name, flipkart_price = scrape_flipkart_product(flipkart_url)

    def clean_price(price_str):
        return Decimal(price_str.replace("₹", "").replace(",", "").strip())

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
