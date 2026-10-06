"""Reglas tecnicas puras compartidas por live paper y backtest."""

import math

import pandas as pd

from core.models import TechnicalSignal


class TechnicalStrategy:

  @staticmethod
  def entry_signal(current: pd.Series, previous: pd.Series) -> TechnicalSignal:
    required = ("close", "sma_200", "ema_20", "sma_50", "macd_hist", "rsi_14")
    if not TechnicalStrategy._valid(current, required):
      return TechnicalSignal("MANTENER", "Indicadores insuficientes para una entrada.")

    conditions = {
        "precio sobre SMA200": current["close"] > current["sma_200"],
        "EMA20 sobre SMA50": current["ema_20"] > current["sma_50"],
        "MACD positivo": current["macd_hist"] > 0,
        "RSI entre 50 y 68": 50 <= current["rsi_14"] <= 68,
    }
    if all(conditions.values()):
      return TechnicalSignal("COMPRAR", ", ".join(conditions.keys()))
    failed = [name for name, passed in conditions.items() if not passed]
    return TechnicalSignal("MANTENER", "No cumple: " + ", ".join(failed))

  @staticmethod
  def exit_signal(current: pd.Series, previous: pd.Series) -> TechnicalSignal:
    required = ("ema_20", "sma_50", "rsi_14")
    if not TechnicalStrategy._valid(current, required):
      return TechnicalSignal("MANTENER", "Indicadores insuficientes para salida tecnica.")
    crossed_down = (
        TechnicalStrategy._valid(previous, ("ema_20", "sma_50"))
        and previous["ema_20"] >= previous["sma_50"]
        and current["ema_20"] < current["sma_50"]
    )
    if crossed_down:
      return TechnicalSignal("VENDER", "Cruce bajista EMA20/SMA50.")
    if current["rsi_14"] < 45:
      return TechnicalSignal("VENDER", "RSI por debajo de 45.")
    return TechnicalSignal("MANTENER", "La tendencia de salida no se activo.")

  @staticmethod
  def _valid(row: pd.Series, fields: tuple[str, ...]) -> bool:
    try:
      return all(math.isfinite(float(row[field])) for field in fields)
    except (KeyError, TypeError, ValueError):
      return False
