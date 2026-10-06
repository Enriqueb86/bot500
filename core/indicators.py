"""Indicadores tecnicos sin dependencias de pandas-ta."""

import numpy as np
import pandas as pd


class TechnicalIndicators:

  @staticmethod
  def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    required = {"open", "high", "low", "close", "volume"}
    if df.empty or not required.issubset(df.columns):
      return pd.DataFrame()

    result = df.copy()
    result["sma_50"] = result["close"].rolling(window=50).mean()
    result["sma_200"] = result["close"].rolling(window=200).mean()
    result["ema_20"] = result["close"].ewm(span=20, adjust=False).mean()

    delta = result["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    average_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = average_gain / average_loss.replace(0, np.nan)
    result["rsi_14"] = (100 - (100 / (1 + rs))).fillna(100.0)

    exp12 = result["close"].ewm(span=12, adjust=False).mean()
    exp26 = result["close"].ewm(span=26, adjust=False).mean()
    result["macd"] = exp12 - exp26
    result["macd_signal"] = result["macd"].ewm(span=9, adjust=False).mean()
    result["macd_hist"] = result["macd"] - result["macd_signal"]

    high_low = result["high"] - result["low"]
    high_close = (result["high"] - result["close"].shift()).abs()
    low_close = (result["low"] - result["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    result["atr_14"] = true_range.ewm(
        alpha=1 / 14, min_periods=14, adjust=False
    ).mean()
    result["volume_sma_20"] = result["volume"].rolling(window=20).mean()

    # Alias temporales para codigo o historiales de la version anterior.
    result["MACD_12_26_9"] = result["macd"]
    result["MACDs_12_26_9"] = result["macd_signal"]
    result["MACDh_12_26_9"] = result["macd_hist"]
    return result
