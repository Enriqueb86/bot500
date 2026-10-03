import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Parámetros del Bot
EXCHANGE_ID = "binance"
SYMBOL = "BTC/USDT,ETH/USDT"
TIMEFRAME = "1h"

# Configuración de Testnet y Capital de Prueba ($100 USD)
USE_TESTNET = True        # Ponlo en False cuando vayas a producción real
PAPER_TRADING = True      # True para simulación local, False para enviar órdenes a Testnet/Live
INITIAL_CAPITAL = 100.0   # Tus 100 dólares iniciales de prueba

# Gestión de Riesgo para $100
MAX_DRAWDOWN_PCT = 0.15   # Límite de pérdida global del 15% ($15)
RISK_PER_TRADE_PCT = 0.02 # Arriesgar 2% ($2) por operación en cuenta pequeña