# src/server.py
from aiohttp import web
import time
import json
from .models import AppState
from .db import get_found_wallets
from .utils import TOKENS_TO_CHECK

async def status_handler(request):
    state: AppState = request.app['state']
    
    uptime_seconds = time.time() - state.start_time
    uptime_str = time.strftime('%H:%M:%S', time.gmtime(uptime_seconds))
    
    rate = state.total_checks / uptime_seconds if uptime_seconds > 0 else 0

    found_wallets = await get_found_wallets()

    html = f"""
    <html>
    <head>
        <title>ETH Hunter Secure</title>
        <meta http-equiv="refresh" content="10">
        <style>
            body {{ font-family: monospace; background-color: #0d1117; color: #c9d1d9; }}
            .container {{ max-width: 1000px; margin: auto; padding: 20px; }}
            h2, h3 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 5px;}}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.9em; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #30363d; }}
            td:nth-child(1) {{ word-break: break-all; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Моніторинг ETH Hunter (v2.1 Secure)</h2>
            <p>Час роботи: {uptime_str}</p>
            <p>Перевірено ключів: {state.total_checks}</p>
            <p>Швидкість: {rate:.2f} ключів/сек</p>
            <p>Знайдено гаманців: {state.wallets_found}</p>
            <p>Помилок RPC: {state.errors}</p>
            <p>Адаптивна затримка: {state.adaptive_delay:.3f} сек</p>
            <p>Відстежувані токени: {', '.join(TOKENS_TO_CHECK.keys())}</p>

            <h3>Останні знахідки (Приватні ключі зашифровано):</h3>
            <table>
                <tr><th>Адреса</th><th>Баланс ETH</th><th>Токени</th><th>Час</th></tr>
    """
    for wallet in found_wallets:
        # Безпечне відображення токенів
        try:
            tokens_dict = json.loads(wallet.get('tokens', '{}'))
            tokens_str = ", ".join([f"{k}: {v:.2f}" for k, v in tokens_dict.items()])
        except:
            tokens_str = "N/A"
            
        html += f"<tr><td>{wallet['address']}</td><td>{wallet['eth_balance']:.6f}</td><td>{tokens_str}</td><td>{wallet['found_at']}</td></tr>"

    html += """
            </table>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def start_web_server(state: AppState):
    app = web.Application()
    app['state'] = state
    app.router.add_get("/", status_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 8080) # Змінено на 127.0.0.1 для безпеки
    await site.start()
    print("Безпечний веб-сервер запущено на http://127.0.0.1:8080")
