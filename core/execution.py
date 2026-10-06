"""Motor de ejecucion paper con persistencia y contabilidad basica."""

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from config.settings import (
    INITIAL_CAPITAL,
    MAX_DRAWDOWN_PCT,
    MIN_NOTIONAL,
    PAPER_TRADING,
    SLIPPAGE_PCT,
    STATE_FILE,
    TRADING_FEE_PCT,
)
from core.models import Position


class ExecutionEngine:

  def __init__(
      self,
      initial_capital: float = INITIAL_CAPITAL,
      fee_pct: float = TRADING_FEE_PCT,
      slippage_pct: float = SLIPPAGE_PCT,
      min_notional: float = MIN_NOTIONAL,
      max_drawdown_pct: float = MAX_DRAWDOWN_PCT,
      state_file: str | Path | None = STATE_FILE,
  ):
    if not PAPER_TRADING:
      raise RuntimeError(
          "La ejecucion real esta bloqueada. Configura PAPER_TRADING=true."
      )
    self.initial_capital = float(initial_capital)
    self.cash = float(initial_capital)
    self.fee_pct = float(fee_pct)
    self.slippage_pct = float(slippage_pct)
    self.min_notional = float(min_notional)
    self.max_drawdown_pct = float(max_drawdown_pct)
    self.peak_equity = float(initial_capital)
    self.positions: dict[str, Position] = {}
    self.last_prices: dict[str, float] = {}
    self.last_processed_candles: dict[str, str] = {}
    self.state_file = Path(state_file) if state_file else None
    self.halted = False
    self._load_state()

  @property
  def balance(self) -> float:
    """Alias compatible: devuelve equity estimado, no solo efectivo."""
    return self.equity()

  @property
  def active_position(self) -> bool:
    return bool(self.positions)

  def has_position(self, symbol: str) -> bool:
    return symbol in self.positions

  def equity(self, prices: dict[str, float] | None = None) -> float:
    prices = prices or self.last_prices
    position_value = 0.0
    for symbol, position in self.positions.items():
      price = float(prices.get(symbol, position.entry_price))
      position_value += price * position.size
    return self.cash + position_value

  def exposure(self, prices: dict[str, float] | None = None) -> float:
    prices = prices or self.last_prices
    return sum(
        float(prices.get(symbol, position.entry_price)) * position.size
        for symbol, position in self.positions.items()
    )

  def drawdown_pct(self) -> float:
    equity = self.equity()
    self.peak_equity = max(self.peak_equity, equity)
    if self.peak_equity <= 0:
      return 1.0
    return max((self.peak_equity - equity) / self.peak_equity, 0.0)

  def update_market_price(self, symbol: str, price: float) -> None:
    if math.isfinite(float(price)) and float(price) > 0:
      self.last_prices[symbol] = float(price)
      if self.drawdown_pct() >= self.max_drawdown_pct:
        self.halted = True
      self._save_state()

  def open_position(
      self,
      symbol: str,
      price: float,
      risk_data: dict[str, float],
      reason: str,
      confidence: int = 0,
      timestamp: str | None = None,
      signal_candle: str = "",
  ) -> dict:
    if self.halted:
      return {"status": "REJECTED", "reason": "Circuit breaker de drawdown activo."}
    if self.has_position(symbol):
      return {"status": "REJECTED", "reason": "Ya existe una posicion para el simbolo."}

    fill_price = float(price) * (1.0 + self.slippage_pct)
    requested_size = float(risk_data.get("position_size", 0.0))
    affordable_size = self.cash / (fill_price * (1.0 + self.fee_pct))
    size = min(requested_size, affordable_size)
    notional = fill_price * size
    if size <= 0 or notional < self.min_notional:
      return {
          "status": "REJECTED",
          "reason": f"Notional {notional:.2f} inferior al minimo {self.min_notional:.2f}.",
      }

    entry_fee = notional * self.fee_pct
    self.cash -= notional + entry_fee
    position = Position(
        symbol=symbol,
        entry_time=timestamp or datetime.now(timezone.utc).isoformat(),
        entry_price=fill_price,
        size=size,
        stop_loss=float(risk_data["stop_loss"]),
        take_profit=float(risk_data["take_profit"]),
        entry_fee=entry_fee,
        signal_candle=signal_candle,
        reason=reason,
        confidence=int(confidence),
    )
    self.positions[symbol] = position
    self.last_prices[symbol] = float(price)
    self._save_state()
    return {
        "status": "OPENED",
        "position": position,
        "fill_price": fill_price,
        "fee": entry_fee,
    }

  def close_position(
      self,
      symbol: str,
      price: float,
      reason: str,
      timestamp: str | None = None,
  ) -> dict:
    position = self.positions.get(symbol)
    if position is None:
      return {"status": "REJECTED", "reason": "No existe una posicion para cerrar."}

    fill_price = float(price) * (1.0 - self.slippage_pct)
    exit_notional = fill_price * position.size
    exit_fee = exit_notional * self.fee_pct
    gross_pnl = (fill_price - position.entry_price) * position.size
    net_pnl = gross_pnl - position.entry_fee - exit_fee
    self.cash += exit_notional - exit_fee
    del self.positions[symbol]
    self.last_prices[symbol] = float(price)
    equity = self.equity()
    self.peak_equity = max(self.peak_equity, equity)
    if self.drawdown_pct() >= self.max_drawdown_pct:
      self.halted = True
    self._save_state()
    return {
        "status": "CLOSED",
        "symbol": symbol,
        "entry_time": position.entry_time,
        "exit_time": timestamp or datetime.now(timezone.utc).isoformat(),
        "entry_price": position.entry_price,
        "exit_price": fill_price,
        "size": position.size,
        "entry_fee": position.entry_fee,
        "exit_fee": exit_fee,
        "gross_pnl": gross_pnl,
        "net_pnl": net_pnl,
        "balance": self.cash,
        "equity": equity,
        "reason": reason,
    }

  def mark_candle_processed(self, symbol: str, timestamp: str) -> None:
    self.last_processed_candles[symbol] = timestamp
    self._save_state()

  def was_candle_processed(self, symbol: str, timestamp: str) -> bool:
    return self.last_processed_candles.get(symbol) == timestamp

  def _save_state(self) -> None:
    if self.state_file is None:
      return
    self.state_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "initial_capital": self.initial_capital,
        "cash": self.cash,
        "peak_equity": self.peak_equity,
        "halted": self.halted,
        "positions": {
            symbol: position.to_dict() for symbol, position in self.positions.items()
        },
        "last_prices": self.last_prices,
        "last_processed_candles": self.last_processed_candles,
    }
    temporary = self.state_file.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(self.state_file)

  def _load_state(self) -> None:
    if self.state_file is None or not self.state_file.exists():
      return
    try:
      payload = json.loads(self.state_file.read_text(encoding="utf-8"))
      self.cash = float(payload["cash"])
      self.peak_equity = float(payload.get("peak_equity", self.initial_capital))
      self.halted = bool(payload.get("halted", False))
      self.positions = {
          symbol: Position.from_dict(position)
          for symbol, position in payload.get("positions", {}).items()
      }
      self.last_prices = {
          symbol: float(price)
          for symbol, price in payload.get("last_prices", {}).items()
      }
      self.last_processed_candles = dict(
          payload.get("last_processed_candles", {})
      )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
      raise RuntimeError(f"Estado paper invalido en {self.state_file}: {exc}") from exc

  def execute_order(
      self, action: str, price: float, risk_data: dict, symbol: str = "BTC/USDT"
  ) -> dict:
    """Compatibilidad temporal con llamadas antiguas."""
    if action == "COMPRAR":
      return self.open_position(symbol, price, risk_data, "Orden legacy")
    if action == "VENDER":
      return self.close_position(symbol, price, "Orden legacy")
    return {"status": "HOLD"}
