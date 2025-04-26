# tracker/models.py

from django.db import models

class ProductPrice(models.Model):
    name = models.CharField(max_length=255)
    price = models.CharField(max_length=20)
    platform = models.CharField(max_length=50)
    scraped_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.platform} - {self.name} - {self.price}"
