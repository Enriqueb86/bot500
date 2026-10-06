"""Acceso de solo lectura a datos publicos del exchange."""

import ccxt
import pandas as pd

from config.settings import EXCHANGE_ID, TIMEFRAME, USE_TESTNET


class DataEngine:

  def __init__(self, use_testnet: bool | None = None):
    exchange_class = getattr(ccxt, EXCHANGE_ID)
    self.exchange = exchange_class({"enableRateLimit": True, "timeout": 15_000})
    sandbox = USE_TESTNET if use_testnet is None else use_testnet
    if sandbox and EXCHANGE_ID == "binance":
      self.exchange.set_sandbox_mode(True)
      print("[INFO] Datos conectados a Binance Testnet.")

  def fetch_ohlcv(self, symbol: str, limit: int = 260) -> pd.DataFrame:
    try:
      ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=limit)
      return self._to_frame(ohlcv)
    except Exception as exc:
      print(f"[ERROR] No se pudo obtener OHLCV para {symbol}: {exc}")
      return pd.DataFrame()

  def fetch_historical_ohlcv(self, symbol: str, candles: int = 2_000) -> pd.DataFrame:
    """Descarga velas paginando hacia adelante para backtesting."""
    try:
      timeframe_ms = self.exchange.parse_timeframe(TIMEFRAME) * 1_000
      since = self.exchange.milliseconds() - ((candles + 5) * timeframe_ms)
      rows: list[list[float]] = []
      while len(rows) < candles:
        requested = min(1_000, candles - len(rows))
        batch = self.exchange.fetch_ohlcv(
            symbol,
            timeframe=TIMEFRAME,
            since=since,
            limit=requested,
        )
        if not batch:
          break
        rows.extend(batch)
        next_since = int(batch[-1][0]) + timeframe_ms
        if next_since <= since:
          break
        since = next_since
        if len(batch) < requested:
          break
      unique = {int(row[0]): row for row in rows}
      ordered = [unique[key] for key in sorted(unique)][-candles:]
      return self._to_frame(ordered)
    except Exception as exc:
      print(f"[ERROR] No se pudo descargar historia de {symbol}: {exc}")
      return pd.DataFrame()

  def fetch_current_ticker(self, symbol: str) -> dict[str, float | str | None]:
    try:
      ticker = self.exchange.fetch_ticker(symbol)
      return {
          "symbol": symbol,
          "last_price": ticker.get("last"),
          "bid": ticker.get("bid"),
          "ask": ticker.get("ask"),
      }
    except Exception as exc:
      print(f"[ERROR] No se pudo obtener ticker para {symbol}: {exc}")
      return {"symbol": symbol, "last_price": None, "bid": None, "ask": None}

  @staticmethod
  def _to_frame(ohlcv: list[list[float]]) -> pd.DataFrame:
    frame = pd.DataFrame(
        ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    if frame.empty:
      return frame
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
    frame.set_index("timestamp", inplace=True)
    return frame
