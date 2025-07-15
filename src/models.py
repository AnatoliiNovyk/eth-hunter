# src/models.py

from dataclasses import dataclass, field
from typing import Dict
import asyncio # <--- Додайте цей імпорт

@dataclass
class Wallet:
    address: str
    private_key: str
    chain: str
    balance_native: float = 0.0
    tokens: Dict[str, float] = field(default_factory=dict)
    tx_count: int = 0
    first_tx_ts: int = 0
    last_tx_ts: int = 0

@dataclass
class AppState:
    total_checks: int = 0
    wallets_found: int = 0
    start_time: float = 0.0
    errors: int = 0
    adaptive_delay: float = 0.05
    chain_stats: Dict[str, Dict] = field(default_factory=lambda: {"total_checks": 0, "wallets_found": 0})
    # --- ДОДАНО НОВИЙ АТРИБУТ ---
    pause_event: asyncio.Event = field(default_factory=asyncio.Event)
