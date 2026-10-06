import unittest

import pandas as pd

from core.execution import ExecutionEngine
from strategies.base_strategy import BaseStrategy


class _Logger:
  def __init__(self):
    self.closed = []

  def log_close(self, result):
    self.closed.append(result)


class BaseStrategyTests(unittest.TestCase):

  def test_does_not_apply_pre_entry_bar_range_to_new_position(self):
    strategy = BaseStrategy.__new__(BaseStrategy)
    strategy.execution_engine = ExecutionEngine(
        initial_capital=100,
        fee_pct=0,
        slippage_pct=0,
        state_file=None,
    )
    strategy.logger = _Logger()
    candle = "2026-10-06T18:00:00+00:00"
    strategy.execution_engine.open_position(
        "BTC/USDT",
        100,
        {"position_size": 0.1, "stop_loss": 95, "take_profit": 110},
        "test",
        signal_candle=candle,
    )
    current = pd.Series({
        "low": 90,
        "high": 105,
        "ema_20": 101,
        "sma_50": 100,
        "rsi_14": 55,
    })
    previous = current.copy()
    result = strategy._manage_position(
        "BTC/USDT", current, previous, 100, candle
    )
    self.assertIsNone(result)
    self.assertTrue(strategy.execution_engine.has_position("BTC/USDT"))

    result = strategy._manage_position(
        "BTC/USDT", current, previous, 100, "2026-10-06T19:00:00+00:00"
    )
    self.assertEqual(result["status"], "CLOSED")
    self.assertFalse(strategy.execution_engine.has_position("BTC/USDT"))


if __name__ == "__main__":
  unittest.main()
