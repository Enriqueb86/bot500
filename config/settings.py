"""Configuracion central del bot.

Los valores sensibles y los parametros que cambian entre entornos se leen desde
``.env``. El proyecto permanece deliberadamente bloqueado en paper trading hasta
que exista evidencia suficiente para habilitar otro modo.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _env_bool(name: str, default: bool) -> bool:
  value = os.getenv(name)
  if value is None:
    return default
  return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
  value = os.getenv(name)
  return default if value is None else float(value)


def _env_int(name: str, default: int) -> int:
  value = os.getenv(name)
  return default if value is None else int(value)


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
AI_ENABLED = _env_bool("AI_ENABLED", False)
AI_MIN_CONFIDENCE = _env_int("AI_MIN_CONFIDENCE", 60)

EXCHANGE_ID = os.getenv("EXCHANGE_ID", "binance")
SYMBOL = os.getenv("SYMBOLS", "BTC/USDT,ETH/USDT")
SYMBOLS = tuple(symbol.strip() for symbol in SYMBOL.split(",") if symbol.strip())
TIMEFRAME = os.getenv("TIMEFRAME", "1h")
OHLCV_LIMIT = max(_env_int("OHLCV_LIMIT", 260), 205)
LOOP_INTERVAL_SECONDS = _env_int("LOOP_INTERVAL_SECONDS", 420)
USE_TESTNET = _env_bool("USE_TESTNET", True)

# Seguridad: por ahora solo se permite simulacion local.
PAPER_TRADING = _env_bool("PAPER_TRADING", True)
INITIAL_CAPITAL = _env_float("INITIAL_CAPITAL", 100.0)
RISK_PER_TRADE_PCT = _env_float("RISK_PER_TRADE_PCT", 0.01)
MAX_DRAWDOWN_PCT = _env_float("MAX_DRAWDOWN_PCT", 0.15)
MAX_TOTAL_EXPOSURE_PCT = _env_float("MAX_TOTAL_EXPOSURE_PCT", 0.40)
STOP_ATR_MULTIPLE = _env_float("STOP_ATR_MULTIPLE", 2.0)
TAKE_PROFIT_R_MULTIPLE = _env_float("TAKE_PROFIT_R_MULTIPLE", 2.0)
TRADING_FEE_PCT = _env_float("TRADING_FEE_PCT", 0.001)
SLIPPAGE_PCT = _env_float("SLIPPAGE_PCT", 0.0005)
MIN_NOTIONAL = _env_float("MIN_NOTIONAL", 5.0)

LOG_DIR = ROOT_DIR / "logs"
STATE_FILE = ROOT_DIR / "state" / "paper_state.json"
