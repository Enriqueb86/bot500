"""Punto de entrada del bot de paper trading."""

import argparse
import time

from config.settings import AI_ENABLED, LOOP_INTERVAL_SECONDS, PAPER_TRADING
from core.dashboard import show_dashboard
from strategies.base_strategy import BaseStrategy


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Crypto bot en paper trading")
  parser.add_argument("--once", action="store_true", help="Ejecuta un solo ciclo.")
  parser.add_argument(
      "--dashboard", action="store_true", help="Muestra resultados y termina."
  )
  return parser.parse_args()


def main() -> None:
  args = parse_args()
  if args.dashboard:
    show_dashboard()
    return
  if not PAPER_TRADING:
    raise RuntimeError("Trading real bloqueado: configura PAPER_TRADING=true.")

  print("Iniciando bot en PAPER TRADING.")
  print(f"Filtro Gemini: {'ACTIVO' if AI_ENABLED else 'DESACTIVADO'}")
  strategy = BaseStrategy()
  try:
    while True:
      strategy.run_cycle()
      if args.once:
        break
      print(f"Esperando proximo ciclo en {LOOP_INTERVAL_SECONDS} segundos...")
      time.sleep(LOOP_INTERVAL_SECONDS)
  except KeyboardInterrupt:
    print("\nBot detenido manualmente.")


if __name__ == "__main__":
  main()
