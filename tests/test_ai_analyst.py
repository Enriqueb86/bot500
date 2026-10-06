import json
import unittest

from core.ai_analyst import AIAnalyst


class _Response:
  text = json.dumps({
      "decision": "REDUCIR_RIESGO",
      "confidence": 80,
      "risk_multiplier": 0.5,
      "reasons": ["volatilidad elevada"],
  })


class _Models:
  def generate_content(self, **_):
    return _Response()


class _Client:
  models = _Models()


class AIAnalystTests(unittest.TestCase):

  def test_disabled_ai_allows_technical_signal(self):
    result = AIAnalyst(enabled=False).filter_entry("BTC/USDT", {}, "test")
    self.assertTrue(result.approved)
    self.assertEqual(result.model, "disabled")

  def test_structured_response_is_validated(self):
    analyst = AIAnalyst(enabled=True, client=_Client(), min_confidence=60)
    result = analyst.filter_entry("BTC/USDT", {"rsi_14": 60}, "test")
    self.assertEqual(result.decision, "REDUCIR_RIESGO")
    self.assertEqual(result.risk_multiplier, 0.5)


if __name__ == "__main__":
  unittest.main()
