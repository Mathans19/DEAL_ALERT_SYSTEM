@csrf_exempt
def telegram_webhook(request):
    if request.method == "POST":
        json_str = request.body.decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return HttpResponse("")
    else:
        return HttpResponse("This endpoint is for Telegram Webhooks.")

def home(request):
    return HttpResponse("""
    <html>
        <head>
            <title>Deal Alert System | Active</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                .card { background: #1e293b; padding: 2rem; border-radius: 1rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; border: 1px solid #334155; }
                .status { color: #22c55e; font-weight: bold; font-size: 1.2rem; }
                h1 { margin-bottom: 0.5rem; }
                p { color: #94a3b8; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🌩️ Deal Alert System</h1>
                <p>Cloud Instance is <span class="status">LIVE</span></p>
                <hr style="border: 0; border-top: 1px solid #334155; margin: 1.5rem 0;">
                <p>Share your links on Telegram to track prices.</p>
            </div>
        </body>
    </html>
    """)
    if request.method == "POST":
        json_str = request.body.decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return HttpResponse("")
    else:
        return HttpResponse("This endpoint is for Telegram Webhooks.")
