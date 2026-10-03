class ExecutionEngine:

  def __init__(self):
    self.balance = 100.0
    self.active_position = False

  def execute_order(
      self, action: str, price: float, risk_data: dict, symbol: str = "BTCUSDT"
  ) -> dict:
    try:
      if action == "COMPRAR":
        self.active_position = True
        print(f"[Ejecución] Orden de COMPRA ejecutada para {symbol} a {price}")
        return {
            "status": "SUCCESS",
            "symbol": symbol,
            "price": price,
            "size": risk_data.get("position_size", 0),
            "profit": 0.0,
        }
      elif action == "VENDER":
        self.active_position = False
        print(f"[Ejecución] Orden de VENTA/CIERRE ejecutada para {symbol} a {price}")
        return {
            "status": "CLOSED",
            "symbol": symbol,
            "closed_order": {"size": risk_data.get("size", 0)},
            "profit": risk_data.get("profit", 0.0),
        }
      return {"status": "HOLD"}
    except Exception as e:
      print(f"[Error] Al ejecutar orden para {symbol}: {e}")
      return {"status": "ERROR"}