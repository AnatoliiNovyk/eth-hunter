# src/core.py
import asyncio
import random
from eth_account import Account
from web3 import Web3
from cryptography.fernet import Fernet
from .models import Wallet, AppState
from .db import save_wallet
from .notifier import notifier
from .utils import ERC20_ABI, TOKENS_TO_CHECK

def generate_wallets_sync(count: int):
    """Синхронна функція, що буде виконуватися в окремому процесі."""
    wallets = []
    for _ in range(count):
        pk = ''.join(random.choice('0123456789abcdef') for _ in range(64))
        try:
            acct = Account.from_key(pk)
            wallets.append(Wallet(address=acct.address, private_key=pk))
        except Exception:
            continue
    return wallets

class CoreLogic:
    def __init__(self, state: AppState, session, rpc_url: str, cipher: Fernet):
        self.state = state
        self.session = session
        self.rpc_url = rpc_url
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.cipher = cipher

    async def check_wallets_batch(self, wallets: list[Wallet]):
        if not wallets: return
        batch_payload = [{"jsonrpc": "2.0", "method": "eth_getBalance", "params": [w.address, "latest"], "id": i} for i, w in enumerate(wallets)]
        try:
            async with self.session.post(self.rpc_url, json=batch_payload) as response:
                if response.status != 200:
                    self.state.errors += 1
                    return
                results = await response.json()
                if not isinstance(results, list): return
                self.state.total_checks += len(wallets)
        except Exception as e:
            self.state.errors += 1; print(f"Помилка RPC: {e}"); return

        for res in results:
            if not isinstance(res, dict): continue
            wallet_index, balance_wei = res.get('id'), int(res.get('result', '0x0'), 16)
            if wallet_index is None: continue
            wallet = wallets[wallet_index]
            wallet.balance_eth = self.w3.from_wei(balance_wei, 'ether')
            if balance_wei > 0:
                self.check_token_balances_sync(wallet)
            if wallet.balance_eth > 0 or wallet.tokens:
                if await save_wallet(wallet, self.cipher):
                    self.state.wallets_found += 1
                    print(f"\n!!! ЗНАЙДЕНО ГАМАНЕЦЬ: {wallet.address} | ETH: {wallet.balance_eth} | Токени: {wallet.tokens}!!!\n")
                    await notifier.send_notification(wallet)

    def check_token_balances_sync(self, wallet: Wallet):
        for symbol, address in TOKENS_TO_CHECK.items():
            try:
                contract = self.w3.eth.contract(address=self.w3.to_checksum_address(address), abi=ERC20_ABI)
                balance = contract.functions.balanceOf(self.w3.to_checksum_address(wallet.address)).call()
                if balance > 0:
                    decimals = contract.functions.decimals().call()
                    wallet.tokens[symbol] = balance / (10 ** decimals)
            except Exception:
                continue

async def worker(state: AppState, session, rpc_url: str, cipher: Fernet, process_executor):
    logic = CoreLogic(state, session, rpc_url, cipher)
    loop = asyncio.get_running_loop()
    while True:
        # Виносимо важку роботу в інший процес
        wallets_to_check = await loop.run_in_executor(
            process_executor, generate_wallets_sync, 50
        )
        if wallets_to_check:
            await logic.check_wallets_batch(wallets_to_check)
        await asyncio.sleep(state.adaptive_delay)
