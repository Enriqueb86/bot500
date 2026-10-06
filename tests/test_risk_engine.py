import unittest

from core.risk_engine import RiskEngine


class RiskEngineTests(unittest.TestCase):

  def test_sizes_position_by_stop_distance_and_caps_notional(self):
    result = RiskEngine.calculate_position_size(
        capital=1_000,
        risk_pct=0.01,
        entry_price=100,
        atr=2,
        max_notional=200,
    )
    self.assertEqual(result["risk_amount"], 10)
    self.assertEqual(result["position_size"], 2)
    self.assertEqual(result["stop_loss"], 96)
    self.assertEqual(result["take_profit"], 108)

  def test_rejects_zero_atr(self):
    with self.assertRaises(ValueError):
      RiskEngine.calculate_position_size(100, 0.01, 100, 0)


if __name__ == "__main__":
  unittest.main()
