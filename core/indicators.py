import numpy as np
import pandas as pd


class TechnicalIndicators:

  @staticmethod
  def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula indicadores técnicos clave usando pandas/numpy de forma nativa

    para evitar problemas de compatibilidad con numba.
    """
    if df.empty or len(df) < 30:
      return df

    # 1. Medias Móviles Simples (SMA) y Exponenciales (EMA)
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['sma_200'] = df['close'].rolling(window=200).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()

    # 2. Índice de Fuerza Relativa (RSI de 14 periodos)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))

    # 3. MACD (Moving Average Convergence Divergence: 12, 26, 9)
    exp12 = df['close'].ewm(span=12, adjust=False).mean()
    exp26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD_12_26_9'] = exp12 - exp26
    df['MACDs_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean()
    df['MACDh_12_26_9'] = df['MACD_12_26_9'] - df['MACDs_12_26_9']

    # 4. Average True Range (ATR de 14 periodos) para volatilidad y Stop-Loss
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(
        axis=1
    )
    df['atr_14'] = true_range.rolling(window=14).mean()

    return df