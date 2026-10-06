"""Resumen de estado y rendimiento del paper trader."""

from core.execution import ExecutionEngine
from core.logger import TradeLogger


def show_dashboard() -> None:
  logger = TradeLogger()
  engine = ExecutionEngine()
  print("=" * 64)
  print("CRYPTO BOT - PAPER TRADING")
  print("=" * 64)
  print(f"Efectivo:        ${engine.cash:.4f}")
  print(f"Equity:          ${engine.equity():.4f}")
  print(f"Exposicion:      ${engine.exposure():.4f}")
  print(f"Drawdown:        {engine.drawdown_pct() * 100:.3f}%")
  print(f"Circuit breaker: {'ACTIVO' if engine.halted else 'normal'}")
  if engine.positions:
    print("\nPosiciones abiertas:")
    for position in engine.positions.values():
      print(
          f"  {position.symbol}: size={position.size:.8f}, "
          f"entry={position.entry_price:.4f}, stop={position.stop_loss:.4f}, "
          f"target={position.take_profit:.4f}"
      )
  else:
    print("\nSin posiciones abiertas.")
  print("\nRendimiento:")
  for key, value in logger.generate_performance_report().items():
    print(f"  {key}: {value}")
  print("=" * 64)


def main() -> None:
  show_dashboard()


if __name__ == "__main__":
  main()
