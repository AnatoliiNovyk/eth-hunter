import os
import time
from .models import Wallet

class WalletAnalyzer:
    def __init__(self, session, api_url, api_key):
        self.session = session
        self.api_url = api_url
        self.api_key = api_key

    async def analyze(self, wallet: Wallet):
        """Збирає історію транзакцій для гаманця."""
        if not self.api_key:
            return
        
        params = {
            "module": "account",
            "action": "txlist",
            "address": wallet.address,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "asc",
            "apikey": self.api_key
        }
        try:
            async with self.session.get(self.api_url, params=params) as response:
                if response.status != 200:
                    return
                data = await response.json()
                if data.get("status") == "1" and data.get("result"):
                    transactions = data["result"]
                    wallet.tx_count = len(transactions)
                    if wallet.tx_count > 0:
                        wallet.first_tx_ts = int(transactions[0]['timeStamp'])
                        wallet.last_tx_ts = int(transactions[-1]['timeStamp'])
        except Exception as e:
            print(f"Помилка аналізу гаманця {wallet.address}: {e}")
