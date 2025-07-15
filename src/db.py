import aiosqlite
import json
from cryptography.fernet import Fernet
from .models import Wallet

DB_PATH = "reaper_found_wallets.db"

async def setup_database():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                chain TEXT NOT NULL,
                private_key_encrypted BLOB NOT NULL,
                native_balance REAL NOT NULL,
                tokens TEXT,
                tx_count INTEGER,
                first_tx_ts INTEGER,
                last_tx_ts INTEGER,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(address, chain)
            )
        """)
        await db.commit()

async def save_wallet(wallet: Wallet, cipher: Fernet):
    async with aiosqlite.connect(DB_PATH) as db:
        encrypted_pk = cipher.encrypt(wallet.private_key.encode('utf-8'))
        tokens_json = json.dumps(wallet.tokens) if wallet.tokens else None
        try:
            await db.execute(
                """INSERT INTO wallets 
                   (address, chain, private_key_encrypted, native_balance, tokens, tx_count, first_tx_ts, last_tx_ts) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (wallet.address, wallet.chain, encrypted_pk, wallet.balance_native, tokens_json, 
                 wallet.tx_count, wallet.first_tx_ts, wallet.last_tx_ts)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def get_found_wallets(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT address, chain, native_balance, tokens, tx_count, found_at FROM wallets ORDER BY id DESC LIMIT ?"
        async with db.execute(query, (limit,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]
