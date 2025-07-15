# main.py
import asyncio
import os
import time
import json
import aiohttp
from dotenv import load_dotenv
from loguru import logger
from cryptography.fernet import Fernet

# Імпортуємо тільки воркера, без зайвих залежностей
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
            # logger.info(f"Спроба відновлення швидкості. Затримку знижено до {state.adaptive_delay:.2f} сек.")

async def handle_console_commands(state: AppState):
    logger.info("Консоль управління активна. Введіть 'help', щоб побачити команди.")
    loop = asyncio.get_running_loop()
    while True:
        try:
            command = await loop.run_in_executor(None, input)
            if command == 'pause':
                if state.pause_event.is_set():
                    state.pause_event.clear(); logger.warning("Процес поставлено на паузу.")
                else: logger.info("Процес вже на паузі.")
            elif command == 'resume':
                if not state.pause_event.is_set():
                    state.pause_event.set(); logger.success("Процес відновлено.")
                else: logger.info("Процес вже активний.")
            elif command == 'stats':
                rate = state.total_checks / (time.time() - state.start_time) if (time.time() - state.start_time) > 0 else 0
                logger.info(f"--- Статистика ---"); logger.info(f"Перевірено: {state.total_checks} | Знайдено: {state.wallets_found} | Швидкість: {rate:.2f} ключ/сек")
                for chain, stats in state.chain_stats.items():
                    logger.info(f"  - {chain.upper()}: {stats['wallets_found']} знайдено / {stats['total_checks']} перевірено")
                logger.info(f"------------------")
            elif command == 'help':
                logger.info("\nДоступні команди:\n  pause  - поставити на паузу\n  resume - відновити роботу\n  stats  - показати статистику\n")
            else: logger.info("Невідома команда. Введіть 'help' для списку команд.")
        except (EOFError, KeyboardInterrupt, asyncio.CancelledError):
            break

async def main():
    load_dotenv()
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key or "YOUR_ENCRYPTION_KEY_HERE" in encryption_key:
        new_key = Fernet.generate_key().decode('utf-8')
        logger.error(f"\nENCRYPTION_KEY={new_key}\n")
        return
    cipher = Fernet(encryption_key.encode('utf-8'))

    with open("config.json", "r") as f:
        chains_config = json.load(f)

    await setup_database()
    
    chain_stats = {name: {"total_checks": 0, "wallets_found": 0} for name in chains_config}
    app_state = AppState(start_time=time.time(), chain_stats=chain_stats)
    app_state.pause_event.set()

    connector = aiohttp.TCPConnector(limit_per_host=200)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        server_task = asyncio.create_task(start_web_server(app_state))
        tasks.append(server_task)
        
        console_task = asyncio.create_task(handle_console_commands(app_state))
        tasks.append(console_task)
        
        adjuster_task = asyncio.create_task(delay_adjuster(app_state))
        tasks.append(adjuster_task)

        # Спрощений запуск воркерів
        for chain_name, config in chains_config.items():
            config['name'] = chain_name
            num_threads = int(os.getenv(f"{chain_name.upper()}_THREADS", 2))
            for _ in range(num_threads):
                 tasks.append(asyncio.create_task(worker(app_state, session, config, cipher)))
            if num_threads > 0:
                logger.info(f"Запущено {num_threads} потоків для мережі {chain_name.upper()}.")
        
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nПроцес зупинено користувачем.")
