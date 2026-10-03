class RiskEngine:

  @staticmethod
  def calculate_position_size(
      capital: float, risk_pct: float, entry_price: float, atr: float
  ) -> dict:
    """Calcula el tamaño de la posición y los niveles de Stop-Loss / Take-Profit

    utilizando el indicador ATR (Average True Range) para gestión de riesgo dinámica.
    """
    # Definimos el Stop Loss a una distancia de 2 veces el ATR
    stop_loss_distance = atr * 2.0
    stop_loss_price = entry_price - stop_loss_distance
    take_profit_price = entry_price + (
        stop_loss_distance * 2.0
    )  # Ratio riesgo/beneficio 1:2

    # Dinero arriesgado en esta operación
    risk_amount = capital * risk_pct

    # Cantidad de criptomoneda a comprar
    position_size = risk_amount / stop_loss_distance

    return {
        'position_size': round(position_size, 6),
        'stop_loss': round(stop_loss_price, 2),
        'take_profit': round(take_profit_price, 2),
        'risk_amount': round(risk_amount, 2),
    }