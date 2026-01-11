import os
import django
from django.conf import settings

from dotenv import load_dotenv
load_dotenv(override=True)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_tracking_project.settings')
django.setup()

from django.db import connection
from tracker.models import TrackedProduct

print(f"DATABASE: {connection.settings_dict['NAME']}")
print(f"HOST: {connection.settings_dict['HOST']}")
print(f"USER: {connection.settings_dict['USER']}")
print(f"PRODUCTS COUNT: {TrackedProduct.objects.count()}")

for p in TrackedProduct.objects.all():
    print(f"- {p.id}: {p.name} ({p.platform})")
