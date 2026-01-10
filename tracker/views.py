import json
import telebot
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .bot_logic import bot

@csrf_exempt
def telegram_webhook(request):
    if request.method == "POST":
        try:
            # Print basic info for logs
            print(f"DEBUG: Received webhook POST. Token present: {bool(bot.token)}")
            
            json_str = request.body.decode('UTF-8')
            if not json_str:
                return HttpResponse("DEBUG FAIL: Empty body", status=400)

            # Manually parse JSON to check for common issues
            try:
                data = json.loads(json_str)
            except Exception as je:
                return HttpResponse(f"DEBUG FAIL: JSON Parse Error: {str(je)}", status=400)

            print(f"DEBUG: Body parsed successfully. Update ID: {data.get('update_id')}")

            update = telebot.types.Update.de_json(json_str)
            bot.process_new_updates([update])
            
            return HttpResponse("OK", status=200)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"CRITICAL WEBHOOK ERROR: {str(e)}\n{error_trace}")
            return HttpResponse(f"CRITICAL ERROR:\n{error_trace}", status=500)
    else:
        return HttpResponse("This endpoint is for Telegram Webhooks.")

def home(request):
    from tracker.models import TrackedProduct
    count = TrackedProduct.objects.count()
    
    # Masked token for debugging
    token = str(bot.token)
    masked_token = token[:10] + "..." + token[-5:] if token and len(token) > 15 else "MISSING"
    
    return HttpResponse(f"""
    <html>
        <head>
            <title>Deal Alert System | Active</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
                .card {{ background: #1e293b; padding: 2.5rem; border-radius: 1.5rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; border: 1px solid #334155; max-width: 400px; width: 100%; }}
                .status {{ color: #22c55e; font-weight: bold; font-size: 1.2rem; }}
                .stat-box {{ background: #0f172a; padding: 1rem; border-radius: 0.75rem; margin: 1.5rem 0; border: 1px solid #1e293b; }}
                h1 {{ margin-bottom: 0.5rem; font-size: 1.8rem; }}
                p {{ color: #94a3b8; }}
                .debug {{ font-size: 0.8rem; color: #64748b; margin-top: 1rem; font-family: monospace; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🌩️ Deal Alert</h1>
                <p>Cloud Instance is <span class="status">LIVE</span></p>
                
                <div class="stat-box">
                    <p style="margin:0; color:#cbd5e1;">Currently Tracking</p>
                    <h2 style="margin:0.5rem 0; color:#f8fafc; font-size: 2rem;">{count} Products</h2>
                </div>
                
                <p>Bot is connected to Telegram.</p>
                <div class="debug">
                    Token: {masked_token}<br>
                    DB: Neon Cloud<br>
                    Mode: Serverless (Sync)
                </div>
                
                <hr style="border: 0; border-top: 1px solid #334155; margin: 1.5rem 0;">
                <p style="font-size: 0.9rem;">Send links to the bot to track prices.</p>
            </div>
        </body>
    </html>
    """)
