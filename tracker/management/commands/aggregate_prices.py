from django.core.management.base import BaseCommand
from tracker.models import TrackedProduct, ProductPrice
from django.db.models import Avg, Max
from django.db import transaction
import os

class Command(BaseCommand):
    help = 'Aggregates old price records into summary rows'

    def handle(self, *args, **options):
        # Default to 250, but allow env var override
        batch_size = int(os.getenv('PRICE_AGG_BATCH_SIZE', 250))
        self.stdout.write(f"Starting aggregation with batch size: {batch_size}")
        
        products = TrackedProduct.objects.all()
        total_aggregated_rows = 0
        
        for product in products:
            # Fetch all raw row IDs ordered by time (oldest first)
            all_ids = list(
                ProductPrice.objects.filter(product=product, is_summary=False)
                .order_by('scraped_at')
                .values_list('id', flat=True)
            )
            
            total_count = len(all_ids)
            
            # We must preserve at least the most recent raw row for alerts.
            if total_count <= 1:
                continue
                
            # Exclude the very last ID (newest) from being aggregated
            ids_to_process = all_ids[:-1]
            
            # Process in chunks
            for i in range(0, len(ids_to_process), batch_size):
                chunk_ids = ids_to_process[i : i + batch_size]
                
                # Only aggregate full batches
                if len(chunk_ids) < batch_size:
                    continue
                
                with transaction.atomic():
                    batch_qs = ProductPrice.objects.filter(id__in=chunk_ids)
                    if not batch_qs.exists():
                        continue

                    stats = batch_qs.aggregate(p=Avg('price'), d=Max('scraped_at'))
                    avg_price = stats['p']
                    max_date = stats['d']
                    
                    if avg_price is None:
                        continue
                        
                    # Create summary row
                    ProductPrice.objects.create(
                        product=product,
                        price=avg_price,
                        scraped_at=max_date,
                        is_summary=True
                    )
                    
                    # Delete raw rows
                    count = batch_qs.delete()[0]
                    total_aggregated_rows += count
                    self.stdout.write(f"  {product.name}: Aggregated {count} rows into 1 summary.")
        
        self.stdout.write(f"Done. Total rows aggregated/deleted: {total_aggregated_rows}")
