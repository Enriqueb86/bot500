from config.settings import SYMBOL  # Importa la configuración de símbolos
from core.ai_analyst import GeminiAnalyst
from core.data_engine import DataEngine
from core.execution import ExecutionEngine
from core.indicators import TechnicalIndicators
from core.logger import TradeLogger
from core.risk_engine import RiskEngine


class BaseStrategy:

  def __init__(self):
    self.data_engine = DataEngine()
    self.ai_analyst = GeminiAnalyst()
    self.execution_engine = ExecutionEngine()
    self.logger = TradeLogger()

    # Convertimos la cadena de símbolos de settings.py en una lista (ej: "BTC/USDT,ETH/USDT" -> ["BTCUSDT", "ETHUSDT"])
    # Limpiamos barras o espacios por si acaso
    raw_symbols = SYMBOL.split(",") if isinstance(SYMBOL, str) else ["BTCUSDT"]
    self.symbols = [s.strip().replace("/", "") for s in raw_symbols]

  def run_cycle(self):
    print("\n--- Ejecutando ciclo del bot para múltiples activos ---")

    for symbol in self.symbols:
      print(f"\n> Analizando activo: {symbol}")

      # 1. Obtener datos OHLCV para el símbolo actual
      df = self.data_engine.fetch_ohlcv(symbol=symbol, limit=250)
      if df.empty:
        print(f"No se pudieron obtener datos del mercado para {symbol}.")
        continue

      # 2. Calcular indicadores técnicos
      df = TechnicalIndicators.calculate_indicators(df)
      latest = df.iloc[-1]

      market_data = {
          'simbolo': symbol,
          'precio_cierre': float(latest['close']),
          'rsi_14': float(latest['rsi_14']),
          'ema_20': float(latest['ema_20']),
          'sma_50': float(latest['sma_50']),
          'atr_14': float(latest['atr_14']),
      }

      # 3. Análisis con Gemini AI
      ai_response = self.ai_analyst.analyze_market(
          market_data,
          news_summary=f"Mercado estable para {symbol} con tendencia técnica mixta.",
      )
      print(f"Decisión de Gemini ({symbol}): {ai_response}")

      decision = ai_response.get("decision", "MANTENER")
      reason = ai_response.get("razon", "")

      # 4. Obtener ticker actual
      ticker = self.data_engine.fetch_current_ticker(symbol=symbol)
      current_price = ticker.get('last_price', latest['close'])

      # 5. Ejecución y gestión de órdenes
      if decision == "COMPRAR" and not self.execution_engine.active_position:
        risk_data = RiskEngine.calculate_position_size(
            capital=self.execution_engine.balance,
            risk_pct=0.02,
            entry_price=current_price,
            atr=latest['atr_14'],
        )
        result = self.execution_engine.execute_order(
            "COMPRAR", current_price, risk_data, symbol=symbol
        )
        if result["status"] == "SUCCESS":
          self.logger.log_trade(
              f"COMPRA_{symbol}",
              current_price,
              risk_data['position_size'],
              0.0,
              self.execution_engine.balance,
              reason,
          )

      elif decision == "VENDER" and self.execution_engine.active_position:
        result = self.execution_engine.execute_order(
            "VENDER", current_price, {}, symbol=symbol
        )
        if result["status"] == "CLOSED":
          self.logger.log_trade(
              f"CIERRE_{symbol}",
              current_price,
              result["closed_order"]["size"],
              result["profit"],
              self.execution_engine.balance,
              reason,
          )
          print(
              "Reporte de Rendimiento:",
              self.logger.generate_performance_report(),
          )