from django.db import models

class TrackedProduct(models.Model):
    PLATFORM_CHOICES = [
        ('Amazon', 'Amazon'),
        ('Flipkart', 'Flipkart'),
    ]
    name = models.CharField(max_length=255)
    url = models.URLField(unique=True)
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES)
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.platform})"

class ProductPrice(models.Model):
    product = models.ForeignKey(TrackedProduct, on_delete=models.CASCADE, related_name='prices')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    scraped_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - ₹{self.price} at {self.scraped_at}"
