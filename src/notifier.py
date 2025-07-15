import os
import telegram
from .models import Wallet

class Notifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.bot = None
        if self.bot_token and self.chat_id:
            try:
                self.bot = telegram.Bot(token=self.bot_token)
            except Exception as e:
                print(f"Помилка ініціалізації Telegram бота: {e}")

    async def send_notification(self, wallet: Wallet):
        if not self.bot:
            return

        message = f"🚨 **ЗНАЙДЕНО ГАМАНЕЦЬ!** 🚨\n\n"
        message += f"**Адреса:** `{wallet.address}`\n"
        message += f"**Приватний ключ:** `{wallet.private_key}`\n"
        message += f"**Баланс ETH:** {wallet.balance_eth:.6f}\n\n"

        if wallet.tokens:
            message += "**Токени (ERC-20):**\n"
            for symbol, amount in wallet.tokens.items():
                message += f"- {symbol}: {amount}\n"
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Помилка відправки сповіщення в Telegram: {e}")

notifier = Notifier()
