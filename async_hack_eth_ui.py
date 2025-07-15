import asyncio
import random
import os
import aiohttp
import stem.control
import datetime
from aiohttp import web
from eth_account import Account
from cryptography.fernet import Fernet
from web3 import Web3
from aiohttp_socks import ProxyConnector

# --- КОНФІГУРАЦІЯ ---
THREAD_COUNT = int(os.getenv("THREAD_COUNT", 200))

# ВАШ URL: Вставте свій RPC URL від Ankr сюди або встановіть змінну середовища
ANKR_RPC_URL = os.getenv("ANKR_RPC_URL", "https://rpc.ankr.com/eth/fc403bd7dfaf1e6568edaf239f6693a5064b4afa2cf6decc4144d8027cd874e4")
# ВИПРАВЛЕНА ПЕРЕВІРКА:
if ANKR_RPC_URL == "YOUR_ANKR_RPC_URL_HERE":
    print("ПОМИЛКА: Будь ласка, вставте ваш реальний RPC URL від Ankr у змінну ANKR_RPC_URL.")
    exit(1)

TOR_PASSWORD = os.getenv("TOR_PASSWORD", "ZXCqwe11@@")

# --- ІНІЦІАЛІЗАЦІЯ ---
if not os.path.exists("log.key"):
    key = Fernet.generate_key()
    with open("log.key", "wb") as f: f.write(key)
else:
    with open("log.key", "rb") as f: key = f.read()

cipher = Fernet(key)
found_count = 0
last_found_time = "—"
w3 = Web3(Web3.HTTPProvider(ANKR_RPC_URL))

def random_private_key():
    return ''.join(random.choice('0123456789abcdef') for _ in range(64))

async def check_balance(session, address):
    """Перевіряє баланс адреси через єдиний надійний RPC від Ankr."""
    payload = {"jsonrpc": "2.0", "method": "eth_getBalance", "params": [address, "latest"], "id": random.randint(1, 999999)}
    try:
        async with session.post(ANKR_RPC_URL, json=payload, timeout=10) as r:
            if r.status == 200:
                data = await r.json()
                return int(data.get("result", "0x0"), 16)
            else:
                print(f"Помилка RPC ({ANKR_RPC_URL}): Статус {r.status}. Можливо, вичерпано ліміт вашого ключа.")
                await asyncio.sleep(10)
                return None
    except Exception as e:
        print(f"Помилка підключення до {ANKR_RPC_URL}: {e}")
        await asyncio.sleep(10)
        return None

async def hack_worker(session, worker_id):
    """Основний воркер, що працює через Ankr."""
    global found_count, last_found_time
    while True:
        try:
            pk = random_private_key()
            acct = Account.from_key(pk)
            bal = await check_balance(session, acct.address)
            if bal is not None and bal > 0:
                eth_balance = w3.from_wei(bal, 'ether')
                res = f'[Async-{worker_id}] Address: {acct.address}, Balance: {eth_balance} ETH, Private Key: {pk}\n'
                print(f"\n!!! ЗНАЙДЕНО ГАМАНЕЦЬ: {res.strip()} !!!\n")
                with open("found_wallets_secure.log", "ab") as f:
                    f.write(cipher.encrypt(res.encode()) + b'\n')
                found_count += 1
                last_found_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            await asyncio.sleep(0.05)
        except Exception as e:
            print(f"Критична помилка у воркері {worker_id}: {e}")
            await asyncio.sleep(5)

async def tor_rotator():
    """TOR для анонімності."""
    while True:
        await asyncio.sleep(300)
        try:
            with stem.control.Controller.from_port(port=9051) as c:
                c.authenticate(password=TOR_PASSWORD)
                c.signal(stem.Signal.NEWNYM)
                print("Ідентичність TOR успішно змінено.")
        except Exception as e:
            print(f"Помилка ротації TOR: {e}.")

async def status(request):
    html = f"""
    <html><head><title>ETH Hunter Status</title><meta http-equiv="refresh" content="10"></head>
    <body><h2>Моніторинг ETH Hunter</h2>
    <p>RPC Провайдер: Ankr</p>
    <p>Знайдено гаманців: {found_count}</p>
    <p>Остання знахідка: {last_found_time}</p>
    <p><a href='/log'>Завантажити лог</a></p></body></html>
    """
    return web.Response(text=html, content_type="text/html")

async def get_log(request):
    return web.FileResponse("found_wallets_secure.log") if os.path.exists("found_wallets_secure.log") else web.Response(text="Лог пустий.", status=404)

async def start_webserver():
    app = web.Application()
    app.router.add_get('/', status)
    app.router.add_get('/log', get_log)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("Веб-сервер запущено на http://0.0.0.0:8080")

async def main():
    connector = ProxyConnector(host='127.0.0.1', port=9050)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [asyncio.create_task(hack_worker(session, i)) for i in range(THREAD_COUNT)]
        tasks.extend([
            asyncio.create_task(tor_rotator()),
            asyncio.create_task(start_webserver())
        ])
        print(f"Запущено {THREAD_COUNT} потоків через Ankr.")
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПроцес зупинено.")
