import tempfile
import unittest
from pathlib import Path

from core.execution import ExecutionEngine


class ExecutionEngineTests(unittest.TestCase):

  def test_open_close_updates_cash_and_pnl(self):
    engine = ExecutionEngine(
        initial_capital=1_000,
        fee_pct=0.001,
        slippage_pct=0,
        state_file=None,
    )
    opened = engine.open_position(
        "BTC/USDT",
        100,
        {"position_size": 0.5, "stop_loss": 95, "take_profit": 110},
        "test",
    )
    self.assertEqual(opened["status"], "OPENED")
    self.assertAlmostEqual(engine.cash, 949.95)
    closed = engine.close_position("BTC/USDT", 110, "target")
    self.assertEqual(closed["status"], "CLOSED")
    self.assertAlmostEqual(closed["net_pnl"], 4.895)
    self.assertAlmostEqual(engine.cash, 1_004.895)

  def test_state_survives_restart(self):
    with tempfile.TemporaryDirectory() as directory:
      state_file = Path(directory) / "state.json"
      first = ExecutionEngine(initial_capital=100, state_file=state_file)
      first.open_position(
          "ETH/USDT",
          10,
          {"position_size": 2, "stop_loss": 8, "take_profit": 14},
          "test",
      )
      second = ExecutionEngine(initial_capital=100, state_file=state_file)
      self.assertTrue(second.has_position("ETH/USDT"))
      self.assertAlmostEqual(
          second.positions["ETH/USDT"].size,
          first.positions["ETH/USDT"].size,
      )


if __name__ == "__main__":
  unittest.main()
