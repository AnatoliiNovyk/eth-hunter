from aiohttp import web
import time
import json
from .models import AppState
from .db import get_found_wallets

async def status_handler(request):
    state: AppState = request.app['state']
    
    uptime_seconds = time.time() - state.start_time
    uptime_str = time.strftime('%H:%M:%S', time.gmtime(uptime_seconds))
    rate = state.total_checks / uptime_seconds if uptime_seconds > 0 else 0

    found_wallets = await get_found_wallets()

    html = f"""
    <html>
    <head>
        <title>Chain Reaper</title>
        <meta http-equiv="refresh" content="10">
        <style>
            body {{ font-family: monospace; background-color: #0d1117; color: #c9d1d9; }}
            .container {{ display: flex; gap: 20px; padding: 20px; }}
            .main, .sidebar {{ background-color: #161b22; padding: 20px; border-radius: 6px; border: 1px solid #30363d;}}
            .main {{ flex-grow: 1; }} .sidebar {{ min-width: 300px; }}
            h2, h3 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 5px;}}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.9em; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #30363d; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="sidebar">
                <h2>Chain Reaper v3.0</h2>
                <p>Час роботи: {uptime_str}</p>
                <p>Швидкість: {rate:.2f} ключ/сек</p>
                <p>Всього знайдено: {state.wallets_found}</p>
                <p>Помилок RPC: {state.errors}</p>
                <h3>Статистика по мережах:</h3>
    """
    for chain, stats in state.chain_stats.items():
        html += f"<p><b>{chain.upper()}:</b> {stats['wallets_found']} знайдено / {stats['total_checks']} перевірено</p>"

    html += """
            </div>
            <div class="main">
                <h3>Останні знахідки (Мульти-мережеві)</h3>
                <table>
                    <tr><th>Мережа</th><th>Адреса</th><th>Баланс</th><th>Токени</th><th>К-ть TX</th></tr>
    """
    for wallet in found_wallets:
        tokens_str = ", ".join([f"{k}: {v:.2f}" for k, v in json.loads(wallet.get('tokens', '{}')).items()])
        html += f"<tr><td>{wallet['chain'].upper()}</td><td>{wallet['address']}</td><td>{wallet['native_balance']:.4f}</td><td>{tokens_str}</td><td>{wallet['tx_count']}</td></tr>"

    html += """
                </table>
            </div>
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
    site = web.TCPSite(runner, '127.0.0.1', 8080)
    await site.start()
    print("Веб-сервер запущено на http://127.0.0.1:8080")
