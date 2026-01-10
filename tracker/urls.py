from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('webhook/', views.telegram_webhook, name='telegram_webhook'),
]
