# main.py
import asyncio
import os
import time
import aiohttp
from dotenv import load_dotenv
from loguru import logger
from cryptography.fernet import Fernet
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import freeze_support

from src.core import worker
from src.db import setup_database
from src.models import AppState
from src.server import start_web_server

async def delay_adjuster(state: AppState):
    while True:
        await asyncio.sleep(30)
        new_delay = max(state.adaptive_delay / 1.5, 0.05)
        if new_delay < state.adaptive_delay:
            state.adaptive_delay = new_delay
            logger.info(f"Спроба відновлення швидкості. Затримку знижено до {state.adaptive_delay:.2f} сек.")

async def main_async():
    load_dotenv()
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key or encryption_key == "YOUR_ENCRYPTION_KEY_HERE":
        new_key = Fernet.generate_key().decode('utf-8')
        logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! УВАГА !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        logger.error("Ключ шифрування (ENCRYPTION_KEY) не знайдено.")
        logger.error(f"СКОПІЮЙТЕ ЦЕЙ РЯДОК та вставте його у ваш файл .env:\nENCRYPTION_KEY={new_key}\n")
        return
    cipher = Fernet(encryption_key.encode('utf-8'))

    THREAD_COUNT = int(os.getenv("THREAD_COUNT", 4)) # Рекомендовано почати з кількості ядер CPU
    ANKR_RPC_URL = os.getenv("ANKR_RPC_URL")
    if not ANKR_RPC_URL or "YOUR_ANKR_RPC_URL_HERE" in ANKR_RPC_URL:
        logger.error("Критична помилка: ANKR_RPC_URL не налаштовано у файлі .env.")
        return

    await setup_database()
    app_state = AppState(start_time=time.time())
    
    # Створюємо пул процесів
    process_executor = ProcessPoolExecutor()

    connector = aiohttp.TCPConnector(limit_per_host=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        server_task = asyncio.create_task(start_web_server(app_state))
        adjuster_task = asyncio.create_task(delay_adjuster(app_state))
        worker_tasks = [
            asyncio.create_task(worker(app_state, session, ANKR_RPC_URL, cipher, process_executor))
            for _ in range(THREAD_COUNT)
        ]
        logger.info(f"Запущено {THREAD_COUNT} потоків. Генерація ключів винесена в окремі процеси.")
        
        try:
            await asyncio.gather(server_task, adjuster_task, *worker_tasks)
        finally:
            process_executor.shutdown()

if __name__ == "__main__":
    # Захист для сумісності з Windows
    freeze_support()
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("\nПроцес зупинено користувачем.")
