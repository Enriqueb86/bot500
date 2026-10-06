import unittest

import pandas as pd

from strategies.technical_strategy import TechnicalStrategy


class TechnicalStrategyTests(unittest.TestCase):

  def test_entry_when_all_conditions_pass(self):
    current = pd.Series({
        "close": 110,
        "sma_200": 100,
        "ema_20": 108,
        "sma_50": 105,
        "macd_hist": 1,
        "rsi_14": 60,
    })
    signal = TechnicalStrategy.entry_signal(current, current)
    self.assertEqual(signal.action, "COMPRAR")

  def test_exit_on_bearish_cross(self):
    previous = pd.Series({"ema_20": 101, "sma_50": 100, "rsi_14": 50})
    current = pd.Series({"ema_20": 99, "sma_50": 100, "rsi_14": 50})
    signal = TechnicalStrategy.exit_signal(current, previous)
    self.assertEqual(signal.action, "VENDER")


if __name__ == "__main__":
  unittest.main()
