"""Backtest reproducible de la estrategia tecnica, sin llamadas a Gemini."""

import argparse
import json
from dataclasses import dataclass

import pandas as pd

from config.settings import (
    INITIAL_CAPITAL,
    MAX_TOTAL_EXPOSURE_PCT,
    RISK_PER_TRADE_PCT,
    STOP_ATR_MULTIPLE,
    TAKE_PROFIT_R_MULTIPLE,
)
from core.data_engine import DataEngine
from core.execution import ExecutionEngine
from core.indicators import TechnicalIndicators
from core.risk_engine import RiskEngine
from strategies.technical_strategy import TechnicalStrategy


@dataclass
class BacktestReport:
  symbol: str
  start: str
  end: str
  candles: int
  closed_trades: int
  wins: int
  losses: int
  win_rate_pct: float
  net_profit: float
  return_pct: float
  max_drawdown_pct: float
  profit_factor: float | None
  expectancy: float
  buy_hold_return_pct: float
  final_equity: float


def run_backtest(frame: pd.DataFrame, symbol: str) -> BacktestReport:
  data = TechnicalIndicators.calculate_indicators(frame).dropna().copy()
  if len(data) < 5:
    raise ValueError("No hay suficientes velas validas despues de calcular indicadores.")

  engine = ExecutionEngine(initial_capital=INITIAL_CAPITAL, state_file=None)
  pnls: list[float] = []
  equity_curve = [INITIAL_CAPITAL]

  # Cada senal usa una vela ya cerrada y se ejecuta en la apertura siguiente.
  for index in range(2, len(data)):
    signal_row = data.iloc[index - 1]
    previous = data.iloc[index - 2]
    bar = data.iloc[index]
    timestamp = data.index[index].isoformat()
    position = engine.positions.get(symbol)

    if position is not None:
      exit_price = None
      reason = ""
      if float(bar["low"]) <= position.stop_loss:
        exit_price, reason = position.stop_loss, "Stop-loss"
      elif float(bar["high"]) >= position.take_profit:
        exit_price, reason = position.take_profit, "Take-profit"
      else:
        exit_signal = TechnicalStrategy.exit_signal(signal_row, previous)
        if exit_signal.action == "VENDER":
          exit_price, reason = float(bar["open"]), exit_signal.reason
      if exit_price is not None:
        result = engine.close_position(symbol, exit_price, reason, timestamp)
        if result["status"] == "CLOSED":
          pnls.append(float(result["net_pnl"]))

    if not engine.has_position(symbol) and not engine.halted:
      entry_signal = TechnicalStrategy.entry_signal(signal_row, previous)
      if entry_signal.action == "COMPRAR":
        entry_price = float(bar["open"])
        equity = engine.equity()
        available = min(
            engine.cash,
            max(equity * MAX_TOTAL_EXPOSURE_PCT - engine.exposure(), 0.0),
        )
        risk = RiskEngine.calculate_position_size(
            capital=equity,
            risk_pct=RISK_PER_TRADE_PCT,
            entry_price=entry_price,
            atr=float(signal_row["atr_14"]),
            stop_atr_multiple=STOP_ATR_MULTIPLE,
            reward_risk_multiple=TAKE_PROFIT_R_MULTIPLE,
            max_notional=available,
        )
        opened = engine.open_position(
            symbol,
            entry_price,
            risk,
            entry_signal.reason,
            timestamp=timestamp,
            signal_candle=data.index[index - 1].isoformat(),
        )
        if opened["status"] == "OPENED":
          position = engine.positions[symbol]
          immediate_exit = None
          immediate_reason = ""
          if float(bar["low"]) <= position.stop_loss:
            immediate_exit, immediate_reason = position.stop_loss, "Stop-loss"
          elif float(bar["high"]) >= position.take_profit:
            immediate_exit, immediate_reason = position.take_profit, "Take-profit"
          if immediate_exit is not None:
            result = engine.close_position(
                symbol, immediate_exit, immediate_reason, timestamp
            )
            if result["status"] == "CLOSED":
              pnls.append(float(result["net_pnl"]))

    engine.update_market_price(symbol, float(bar["close"]))
    equity_curve.append(engine.equity())

  if engine.has_position(symbol):
    result = engine.close_position(
        symbol, float(data.iloc[-1]["close"]), "Fin del backtest", data.index[-1].isoformat()
    )
    if result["status"] == "CLOSED":
      pnls.append(float(result["net_pnl"]))
      equity_curve.append(engine.equity())

  wins = [pnl for pnl in pnls if pnl > 0]
  losses = [pnl for pnl in pnls if pnl <= 0]
  gross_loss = abs(sum(losses))
  peak = equity_curve[0]
  max_drawdown = 0.0
  for equity in equity_curve:
    peak = max(peak, equity)
    max_drawdown = max(max_drawdown, (peak - equity) / peak if peak else 0.0)
  final_equity = engine.equity()
  first_close = float(data.iloc[0]["close"])
  last_close = float(data.iloc[-1]["close"])
  return BacktestReport(
      symbol=symbol,
      start=data.index[0].isoformat(),
      end=data.index[-1].isoformat(),
      candles=len(data),
      closed_trades=len(pnls),
      wins=len(wins),
      losses=len(losses),
      win_rate_pct=round(len(wins) / len(pnls) * 100, 3) if pnls else 0.0,
      net_profit=round(sum(pnls), 4),
      return_pct=round((final_equity / INITIAL_CAPITAL - 1) * 100, 3),
      max_drawdown_pct=round(max_drawdown * 100, 3),
      profit_factor=round(sum(wins) / gross_loss, 3) if gross_loss else None,
      expectancy=round(sum(pnls) / len(pnls), 4) if pnls else 0.0,
      buy_hold_return_pct=round((last_close / first_close - 1) * 100, 3),
      final_equity=round(final_equity, 4),
  )


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Backtest tecnico sin Gemini")
  parser.add_argument("--symbol", default="BTC/USDT")
  parser.add_argument("--candles", type=int, default=2_000)
  parser.add_argument("--csv", help="CSV OHLCV opcional con columna timestamp.")
  return parser.parse_args()


def main() -> None:
  args = parse_args()
  if args.csv:
    frame = pd.read_csv(args.csv, parse_dates=["timestamp"]).set_index("timestamp")
  else:
    # El backtest usa datos publicos de produccion; nunca envia ordenes.
    frame = DataEngine(use_testnet=False).fetch_historical_ohlcv(
        args.symbol, args.candles
    )
    if not frame.empty:
      frame = frame.iloc[:-1]  # Excluye la vela posiblemente abierta.
  if frame.empty:
    raise RuntimeError("No se pudieron obtener datos para el backtest.")
  report = run_backtest(frame, args.symbol)
  print(json.dumps(report.__dict__, indent=2, ensure_ascii=False))


if __name__ == "__main__":
  main()
