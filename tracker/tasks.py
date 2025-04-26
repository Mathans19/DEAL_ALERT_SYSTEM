from celery import shared_task
from .scraper import save_to_db  # Import the right function

@shared_task
def scrape_and_store_product_data():
    save_to_db()  # This stores scraped data to DB
