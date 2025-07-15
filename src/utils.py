# Мінімальний ABI для отримання балансу ERC-20
ERC20_ABI = """
[
    {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}
]
"""

# Список популярних токенів для перевірки
TOKENS_TO_CHECK = {
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "SHIB": "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE",
    "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    "MATIC": "0x7D1AfA7B718fb893dB30A3aBc0C4c6a9Ac2BB04D" # Polygon (PoS)
}
