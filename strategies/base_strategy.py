"""Orquestacion del ciclo de paper trading."""

import math
from typing import Any

import pandas as pd

from config.settings import (
    MAX_TOTAL_EXPOSURE_PCT,
    OHLCV_LIMIT,
    RISK_PER_TRADE_PCT,
    STOP_ATR_MULTIPLE,
    SYMBOLS,
    TAKE_PROFIT_R_MULTIPLE,
    TIMEFRAME,
)
from core.ai_analyst import AIAnalyst
from core.data_engine import DataEngine
from core.execution import ExecutionEngine
from core.indicators import TechnicalIndicators
from core.logger import TradeLogger
from core.risk_engine import RiskEngine
from strategies.technical_strategy import TechnicalStrategy


class BaseStrategy:

  def __init__(
      self,
      data_engine: DataEngine | None = None,
      ai_analyst: AIAnalyst | None = None,
      execution_engine: ExecutionEngine | None = None,
      logger: TradeLogger | None = None,
  ):
    self.data_engine = data_engine or DataEngine()
    self.ai_analyst = ai_analyst or AIAnalyst()
    self.execution_engine = execution_engine or ExecutionEngine()
    self.logger = logger or TradeLogger()
    self.symbols = list(SYMBOLS)

  def run_cycle(self) -> list[dict[str, Any]]:
    print("\n--- Ciclo de paper trading ---")
    summaries = []
    for symbol in self.symbols:
      try:
        summaries.append(self._run_symbol(symbol))
      except Exception as exc:
        print(f"[ERROR] Ciclo de {symbol} fallo sin detener los demas: {exc}")
        summaries.append({"symbol": symbol, "status": "ERROR", "error": str(exc)})
    self._log_equity()
    return summaries

  def _run_symbol(self, symbol: str) -> dict[str, Any]:
    frame = self.data_engine.fetch_ohlcv(symbol=symbol, limit=OHLCV_LIMIT)
    if len(frame) < 203:
      message = f"Datos insuficientes: {len(frame)} velas; se requieren al menos 203."
      print(f"[{symbol}] {message}")
      return {"symbol": symbol, "status": "NO_DATA", "reason": message}

    frame = TechnicalIndicators.calculate_indicators(frame)
    # La ultima fila suele ser la vela aun abierta. Solo se generan senales con -2.
    current = frame.iloc[-2]
    previous = frame.iloc[-3]
    candle_timestamp = frame.index[-2].isoformat()
    fallback_price = float(current["close"])
    ticker = self.data_engine.fetch_current_ticker(symbol)
    ticker_price = ticker.get("last_price")
    current_price = (
        float(ticker_price)
        if ticker_price is not None and math.isfinite(float(ticker_price))
        else fallback_price
    )
    self.execution_engine.update_market_price(symbol, current_price)

    # Los stops intraperiodo se revisan aun si esta vela ya fue procesada.
    close_result = self._manage_position(
        symbol, current, previous, current_price, candle_timestamp
    )
    if close_result:
      self.execution_engine.mark_candle_processed(symbol, candle_timestamp)
      return close_result

    if self.execution_engine.was_candle_processed(symbol, candle_timestamp):
      print(f"[{symbol}] Vela {candle_timestamp} ya procesada; sin duplicar senal.")
      return {"symbol": symbol, "status": "DUPLICATE_CANDLE"}

    technical = TechnicalStrategy.entry_signal(current, previous)
    ai_decision = "NO_CONSULTADO"
    ai_confidence = 0
    ai_multiplier = 1.0
    ai_reasons = ""
    final_action = technical.action
    result: dict[str, Any] = {
        "symbol": symbol,
        "status": technical.action,
        "reason": technical.reason,
    }

    if technical.action == "COMPRAR" and not self.execution_engine.has_position(symbol):
      market_data = self._market_data(current)
      ai_result = self.ai_analyst.filter_entry(symbol, market_data, technical.reason)
      ai_decision = ai_result.decision
      ai_confidence = ai_result.confidence
      ai_multiplier = ai_result.risk_multiplier
      ai_reasons = "; ".join(ai_result.reasons)
      if not ai_result.approved:
        final_action = "MANTENER"
        result = {"symbol": symbol, "status": "AI_REJECTED", "reason": ai_reasons}
      else:
        result = self._open_position(
            symbol=symbol,
            price=current_price,
            atr=float(current["atr_14"]),
            candle_timestamp=candle_timestamp,
            reason=f"{technical.reason} | Gemini: {ai_reasons}",
            confidence=ai_confidence,
            risk_multiplier=ai_multiplier,
        )
        final_action = "COMPRAR" if result["status"] == "OPENED" else "MANTENER"

    self.logger.log_signal({
        "timestamp": TradeLogger._now(),
        "candle_timestamp": candle_timestamp,
        "symbol": symbol,
        "timeframe": TIMEFRAME,
        "close": current["close"],
        "rsi_14": current["rsi_14"],
        "ema_20": current["ema_20"],
        "sma_50": current["sma_50"],
        "sma_200": current["sma_200"],
        "macd_hist": current["macd_hist"],
        "atr_14": current["atr_14"],
        "technical_action": technical.action,
        "technical_reason": technical.reason,
        "ai_decision": ai_decision,
        "ai_confidence": ai_confidence,
        "ai_risk_multiplier": ai_multiplier,
        "ai_reasons": ai_reasons,
        "final_action": final_action,
    })
    self.execution_engine.mark_candle_processed(symbol, candle_timestamp)
    print(f"[{symbol}] {result['status']}: {result.get('reason', technical.reason)}")
    return result

  def _manage_position(
      self,
      symbol: str,
      current: pd.Series,
      previous: pd.Series,
      current_price: float,
      candle_timestamp: str,
  ) -> dict[str, Any] | None:
    position = self.execution_engine.positions.get(symbol)
    if position is None:
      return None

    exit_price = None
    reason = ""
    bar_after_entry = candle_timestamp != position.signal_candle
    # Si ambos niveles aparecen en una vela, se asume primero el stop (conservador).
    if bar_after_entry and float(current["low"]) <= position.stop_loss:
      exit_price = position.stop_loss
      reason = "Stop-loss alcanzado."
    elif bar_after_entry and float(current["high"]) >= position.take_profit:
      exit_price = position.take_profit
      reason = "Take-profit alcanzado."
    elif current_price <= position.stop_loss:
      exit_price = position.stop_loss
      reason = "Stop-loss intraperiodo alcanzado."
    elif current_price >= position.take_profit:
      exit_price = position.take_profit
      reason = "Take-profit intraperiodo alcanzado."
    elif self.execution_engine.halted:
      exit_price = current_price
      reason = "Cierre por circuit breaker de drawdown."
    elif bar_after_entry:
      signal = TechnicalStrategy.exit_signal(current, previous)
      if signal.action == "VENDER":
        exit_price = current_price
        reason = signal.reason

    if exit_price is None:
      return None
    result = self.execution_engine.close_position(
        symbol, exit_price, reason, timestamp=candle_timestamp
    )
    if result["status"] == "CLOSED":
      self.logger.log_close(result)
      print(f"[{symbol}] CLOSED: P&L neto {result['net_pnl']:.4f} - {reason}")
    return {"symbol": symbol, **result}

  def _open_position(
      self,
      symbol: str,
      price: float,
      atr: float,
      candle_timestamp: str,
      reason: str,
      confidence: int,
      risk_multiplier: float,
  ) -> dict[str, Any]:
    equity = self.execution_engine.equity()
    max_exposure = equity * MAX_TOTAL_EXPOSURE_PCT
    remaining_exposure = max(
        max_exposure - self.execution_engine.exposure(), 0.0
    )
    risk_data = RiskEngine.calculate_position_size(
        capital=equity,
        risk_pct=RISK_PER_TRADE_PCT,
        entry_price=price,
        atr=atr,
        stop_atr_multiple=STOP_ATR_MULTIPLE,
        reward_risk_multiple=TAKE_PROFIT_R_MULTIPLE,
        max_notional=min(remaining_exposure, self.execution_engine.cash),
        risk_multiplier=risk_multiplier,
    )
    result = self.execution_engine.open_position(
        symbol=symbol,
        price=price,
        risk_data=risk_data,
        reason=reason,
        confidence=confidence,
        signal_candle=candle_timestamp,
    )
    if result["status"] == "OPENED":
      self.logger.log_open(
          result["position"],
          self.execution_engine.cash,
          self.execution_engine.equity(),
      )
      return {
          "symbol": symbol,
          "status": "OPENED",
          "reason": reason,
          "fill_price": result["fill_price"],
          "size": result["position"].size,
      }
    return {"symbol": symbol, **result}

  @staticmethod
  def _market_data(row: pd.Series) -> dict[str, float | str]:
    return {
        "timeframe": TIMEFRAME,
        "close": float(row["close"]),
        "rsi_14": float(row["rsi_14"]),
        "ema_20": float(row["ema_20"]),
        "sma_50": float(row["sma_50"]),
        "sma_200": float(row["sma_200"]),
        "macd_hist": float(row["macd_hist"]),
        "atr_14": float(row["atr_14"]),
        "volume": float(row["volume"]),
        "volume_sma_20": float(row["volume_sma_20"]),
    }

  def _log_equity(self) -> None:
    self.logger.log_equity(
        cash=self.execution_engine.cash,
        equity=self.execution_engine.equity(),
        exposure=self.execution_engine.exposure(),
        drawdown_pct=self.execution_engine.drawdown_pct(),
        open_positions=len(self.execution_engine.positions),
    )
