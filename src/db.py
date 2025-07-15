# src/db.py

import aiosqlite
import json
from cryptography.fernet import Fernet
from .models import Wallet

DB_PATH = "found_wallets.db"

async def setup_database():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE NOT NULL,
                private_key_encrypted BLOB NOT NULL, -- Змінено тип для шифрованих даних
                eth_balance REAL NOT NULL,
                tokens TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def save_wallet(wallet: Wallet, cipher: Fernet):
    """Шифрує приватний ключ перед збереженням."""
    async with aiosqlite.connect(DB_PATH) as db:
        tokens_json = json.dumps(wallet.tokens) if wallet.tokens else None
        
        # Шифруємо приватний ключ
        encrypted_pk = cipher.encrypt(wallet.private_key.encode('utf-8'))
        
        try:
            await db.execute(
                "INSERT INTO wallets (address, private_key_encrypted, eth_balance, tokens) VALUES (?, ?, ?, ?)",
                (wallet.address, encrypted_pk, wallet.balance_eth, tokens_json)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def get_found_wallets(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Ми не витягуємо ключ для відображення у веб-інтерфейсі для безпеки
        async with db.execute("SELECT address, eth_balance, tokens, found_at FROM wallets ORDER BY id DESC LIMIT ?", (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
