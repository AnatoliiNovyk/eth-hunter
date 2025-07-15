# src/core.py

import asyncio
import random
import os
from eth_account import Account
from web3 import Web3
from cryptography.fernet import Fernet
from .models import Wallet, AppState
from .db import save_wallet
from .notifier import notifier
from .utils import ERC20_ABI
from .analysis import WalletAnalyzer

def generate_wallets_sync(count: int, chain_name: str):
    wallets = []
    for _ in range(count):
        pk = ''.join(random.choice('0123456789abcdef') for _ in range(64))
        try:
            acct = Account.from_key(pk)
            wallets.append(Wallet(address=acct.address, private_key=pk, chain=chain_name))
        except Exception:
            continue
    return wallets

class CoreLogic:
    def __init__(self, state: AppState, session, chain_config: dict, cipher: Fernet):
        self.state = state
        self.session = session
        self.chain_config = chain_config
        self.cipher = cipher
        self.w3 = Web3(Web3.HTTPProvider(chain_config['rpc_url']))
        self.analyzer = WalletAnalyzer(
            session,
            chain_config['explorer_api_url'],
            os.getenv(chain_config['explorer_api_key_env'])
        )

    async def check_wallets_batch(self, wallets: list[Wallet]):
        if not wallets: return
        batch_payload = [{"jsonrpc": "2.0", "method": "eth_getBalance", "params": [w.address, "latest"], "id": i} for i, w in enumerate(wallets)]

        try:
            async with self.session.post(self.chain_config['rpc_url'], json=batch_payload) as response:
                if response.status != 200:
                    self.state.errors += 1; return
                results = await response.json()
                if not isinstance(results, list): return
                self.state.chain_stats[self.chain_config['name']]['total_checks'] += len(wallets)
                self.state.total_checks += len(wallets)
        except Exception as e:
            self.state.errors += 1; print(f"Помилка RPC [{self.chain_config['name']}]: {e}"); return

        for res in results:
            if not isinstance(res, dict): continue
            wallet_index, balance_wei = res.get('id'), int(res.get('result', '0x0'), 16)
            if wallet_index is None: continue

            if balance_wei > 0:
                wallet = wallets[wallet_index]
                wallet.balance_native = self.w3.from_wei(balance_wei, 'ether')
                self.check_token_balances_sync(wallet)

                if wallet.balance_native > 0 or wallet.tokens:
                    await self.analyzer.analyze(wallet)
                    if await save_wallet(wallet, self.cipher):
                        self.state.wallets_found += 1
                        self.state.chain_stats[self.chain_config['name']]['wallets_found'] += 1
                        print(f"\n!!! [{wallet.chain.upper()}] ЗНАЙДЕНО ГАМАНЕЦЬ: {wallet.address} | {self.chain_config['symbol']}: {wallet.balance_native} | Токени: {wallet.tokens} | TXs: {wallet.tx_count} !!!\n")
                        await notifier.send_notification(wallet)

    def check_token_balances_sync(self, wallet: Wallet):
        tokens_to_check = self.chain_config.get('tokens', {})
        for symbol, address in tokens_to_check.items():
            try:
                contract = self.w3.eth.contract(address=self.w3.to_checksum_address(address), abi=ERC20_ABI)
                balance = contract.functions.balanceOf(self.w3.to_checksum_address(wallet.address)).call()
                if balance > 0:
                    decimals = contract.functions.decimals().call()
                    wallet.tokens[symbol] = balance / (10 ** decimals)
            except Exception:
                continue

async def worker(state: AppState, session, chain_config: dict, cipher: Fernet, process_executor):
    logic = CoreLogic(state, session, chain_config, cipher)
    loop = asyncio.get_running_loop()
    chain_name = chain_config['name']

    while True:
        # Перевірка паузи перед кожною ітерацією
        await state.pause_event.wait()

        wallets_to_check = await loop.run_in_executor(
            process_executor, generate_wallets_sync, 50, chain_name
        )
        if wallets_to_check:
            await logic.check_wallets_batch(wallets_to_check)
        await asyncio.sleep(state.adaptive_delay)
