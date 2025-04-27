from celery import shared_task
from price_tracking_project.track_prices import save_to_db  # Import the function to save to DB

@shared_task
def scrape_and_save():
    save_to_db()
