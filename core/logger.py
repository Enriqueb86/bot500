"""Registro auditable de senales, operaciones y curva de capital."""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import INITIAL_CAPITAL, LOG_DIR


class TradeLogger:

  SIGNAL_FIELDS = (
      "timestamp", "candle_timestamp", "symbol", "timeframe", "close",
      "rsi_14", "ema_20", "sma_50", "sma_200", "macd_hist", "atr_14",
      "technical_action", "technical_reason", "ai_decision", "ai_confidence",
      "ai_risk_multiplier", "ai_reasons", "final_action",
  )
  TRADE_FIELDS = (
      "timestamp", "event", "symbol", "entry_time", "exit_time", "entry_price",
      "exit_price", "size", "stop_loss", "take_profit", "entry_fee", "exit_fee",
      "gross_pnl", "net_pnl", "cash", "equity", "reason", "confidence",
  )
  EQUITY_FIELDS = (
      "timestamp", "cash", "equity", "exposure", "drawdown_pct", "open_positions",
  )

  def __init__(self, log_dir: str | Path = LOG_DIR):
    self.log_dir = Path(log_dir)
    self.log_dir.mkdir(parents=True, exist_ok=True)
    self.signals_file = self.log_dir / "signals.csv"
    self.trades_file = self.log_dir / "trades.csv"
    self.equity_file = self.log_dir / "equity.csv"
    self._ensure_file(self.signals_file, self.SIGNAL_FIELDS)
    self._ensure_file(self.trades_file, self.TRADE_FIELDS)
    self._ensure_file(self.equity_file, self.EQUITY_FIELDS)

  def log_signal(self, data: dict[str, Any]) -> None:
    self._append(self.signals_file, self.SIGNAL_FIELDS, data)

  def log_open(self, position: Any, cash: float, equity: float) -> None:
    self._append(self.trades_file, self.TRADE_FIELDS, {
        "timestamp": self._now(),
        "event": "OPEN",
        "symbol": position.symbol,
        "entry_time": position.entry_time,
        "entry_price": position.entry_price,
        "size": position.size,
        "stop_loss": position.stop_loss,
        "take_profit": position.take_profit,
        "entry_fee": position.entry_fee,
        "cash": cash,
        "equity": equity,
        "reason": position.reason,
        "confidence": position.confidence,
    })

  def log_close(self, result: dict[str, Any]) -> None:
    row = dict(result)
    row.update({"timestamp": self._now(), "event": "CLOSE", "cash": result["balance"]})
    self._append(self.trades_file, self.TRADE_FIELDS, row)

  def log_equity(
      self,
      cash: float,
      equity: float,
      exposure: float,
      drawdown_pct: float,
      open_positions: int,
  ) -> None:
    self._append(self.equity_file, self.EQUITY_FIELDS, {
        "timestamp": self._now(),
        "cash": cash,
        "equity": equity,
        "exposure": exposure,
        "drawdown_pct": drawdown_pct,
        "open_positions": open_positions,
    })

  def generate_performance_report(self) -> dict[str, Any]:
    closed: list[dict[str, str]] = []
    if self.trades_file.exists():
      with self.trades_file.open(newline="", encoding="utf-8") as handle:
        closed = [row for row in csv.DictReader(handle) if row["event"] == "CLOSE"]
    if not closed:
      return {"mensaje": "Aun no hay operaciones cerradas."}

    pnls = [float(row["net_pnl"]) for row in closed]
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl <= 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    net_profit = sum(pnls)
    max_drawdown = self._max_logged_drawdown()
    return {
        "operaciones_cerradas": len(pnls),
        "ganadoras": len(wins),
        "perdedoras": len(losses),
        "win_rate_pct": round(len(wins) / len(pnls) * 100, 2),
        "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss else None,
        "beneficio_neto": round(net_profit, 4),
        "retorno_pct": round(net_profit / INITIAL_CAPITAL * 100, 3),
        "expectancy": round(net_profit / len(pnls), 4),
        "max_drawdown_pct": round(max_drawdown * 100, 3),
    }

  def log_trade(
      self,
      action: str,
      price: float,
      size: float,
      pnl: float,
      balance: float,
      reason: str,
  ) -> None:
    """Compatibilidad con el logger anterior."""
    self._append(self.trades_file, self.TRADE_FIELDS, {
        "timestamp": self._now(),
        "event": "CLOSE" if "CIERRE" in action or "VENTA" in action else "OPEN",
        "symbol": action.split("_", 1)[-1] if "_" in action else "UNKNOWN",
        "entry_price": price,
        "exit_price": price,
        "size": size,
        "net_pnl": pnl,
        "cash": balance,
        "equity": balance,
        "reason": reason,
    })

  def _max_logged_drawdown(self) -> float:
    if not self.equity_file.exists():
      return 0.0
    with self.equity_file.open(newline="", encoding="utf-8") as handle:
      values = [float(row["drawdown_pct"]) for row in csv.DictReader(handle)]
    return max(values, default=0.0)

  @staticmethod
  def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

  @staticmethod
  def _ensure_file(path: Path, fields: tuple[str, ...]) -> None:
    if path.exists() and path.stat().st_size > 0:
      return
    with path.open("w", newline="", encoding="utf-8") as handle:
      csv.DictWriter(handle, fieldnames=fields).writeheader()

  @staticmethod
  def _append(path: Path, fields: tuple[str, ...], data: dict[str, Any]) -> None:
    row = {field: data.get(field, "") for field in fields}
    with path.open("a", newline="", encoding="utf-8") as handle:
      csv.DictWriter(handle, fieldnames=fields).writerow(row)
