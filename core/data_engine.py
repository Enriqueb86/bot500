import ccxt
import pandas as pd
from config.settings import EXCHANGE_ID, SYMBOL, TIMEFRAME, USE_TESTNET


class DataEngine:

  def __init__(self):
    exchange_class = getattr(ccxt, EXCHANGE_ID)
    self.exchange = exchange_class({
        'enableRateLimit': True,
    })

    # Si habilitamos Testnet en settings
    if USE_TESTNET:
      if EXCHANGE_ID == 'binance':
        self.exchange.set_sandbox_mode(True)
        print("[INFO] Conectado a BINANCE TESTNET (Dinero Ficticio)")

  def fetch_ohlcv(self, symbol: str = SYMBOL, limit: int = 250) -> pd.DataFrame:
    try:
      # Usamos el símbolo que se pase por parámetro
      ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=limit)
      df = pd.DataFrame(
          ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
      )
      df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
      df.set_index('timestamp', inplace=True)
      return df
    except Exception as e:
      print(f"[Error] Al obtener datos de CCXT para {symbol}: {e}")
      return pd.DataFrame()

  def fetch_current_ticker(self, symbol: str = SYMBOL) -> dict:
    try:
      ticker = self.exchange.fetch_ticker(symbol)
      return {
          'symbol': symbol,
          'last_price': ticker.get('last'),
          'bid': ticker.get('bid'),
          'ask': ticker.get('ask'),
      }
    except Exception as e:
      print(f"[Error] Al obtener ticker actual para {symbol}: {e}")
      return {}