"""Calculos de riesgo deterministas y reutilizables."""

import math


class RiskEngine:

  @staticmethod
  def calculate_position_size(
      capital: float,
      risk_pct: float,
      entry_price: float,
      atr: float,
      stop_atr_multiple: float = 2.0,
      reward_risk_multiple: float = 2.0,
      max_notional: float | None = None,
      risk_multiplier: float = 1.0,
  ) -> dict[str, float]:
    values = (capital, risk_pct, entry_price, atr, stop_atr_multiple)
    if not all(math.isfinite(float(value)) and float(value) > 0 for value in values):
      raise ValueError("Capital, riesgo, precio, ATR y multiplicador deben ser positivos.")

    risk_multiplier = min(max(float(risk_multiplier), 0.0), 1.0)
    stop_loss_distance = float(atr) * float(stop_atr_multiple)
    risk_amount = float(capital) * float(risk_pct) * risk_multiplier
    position_size = risk_amount / stop_loss_distance

    if max_notional is not None:
      if max_notional <= 0:
        position_size = 0.0
      else:
        position_size = min(position_size, float(max_notional) / float(entry_price))

    stop_loss_price = max(float(entry_price) - stop_loss_distance, 0.0)
    take_profit_price = float(entry_price) + (
        stop_loss_distance * float(reward_risk_multiple)
    )

    return {
        "position_size": round(position_size, 8),
        "stop_loss": round(stop_loss_price, 8),
        "take_profit": round(take_profit_price, 8),
        "risk_amount": round(risk_amount, 8),
        "stop_distance": round(stop_loss_distance, 8),
    }
