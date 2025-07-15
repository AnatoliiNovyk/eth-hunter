# src/models.py

from dataclasses import dataclass, field
from typing import Dict

@dataclass
class Wallet:
    address: str
    private_key: str
    balance_eth: float = 0.0
    tokens: Dict[str, float] = field(default_factory=dict)

@dataclass
class AppState:
    total_checks: int = 0
    wallets_found: int = 0
    start_time: float = 0.0
    errors: int = 0
    adaptive_delay: float = 0.05 # <--- ДОДАНО ЦЕЙ РЯДОК (базова затримка 50ms)
