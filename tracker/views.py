import json
import telebot
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .bot_logic import bot  # We will move bot logic here

@csrf_exempt
def telegram_webhook(request):
    if request.method == "POST":
        json_str = request.body.decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return HttpResponse("")
    else:
        return HttpResponse("This endpoint is for Telegram Webhooks.")
