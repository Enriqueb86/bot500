"""Filtro opcional de riesgo con Gemini.

Gemini no crea la senal principal. Solo puede aprobar, rechazar o reducir el
riesgo de una entrada tecnica ya generada.
"""

import json
from typing import Any

from google import genai
from google.genai import types

from config.settings import (
    AI_ENABLED,
    AI_MIN_CONFIDENCE,
    GEMINI_API_KEY,
    GEMINI_MODEL,
)
from core.models import AIFilterResult


class AIAnalyst:

  def __init__(
      self,
      enabled: bool = AI_ENABLED,
      api_key: str | None = GEMINI_API_KEY,
      model_name: str = GEMINI_MODEL,
      min_confidence: int = AI_MIN_CONFIDENCE,
      client: Any | None = None,
  ):
    self.enabled = enabled
    self.model_name = model_name
    self.min_confidence = min_confidence
    self.client = client
    if self.enabled and self.client is None and api_key:
      self.client = genai.Client(
          api_key=api_key,
          http_options=types.HttpOptions(
              timeout=20_000,
              retry_options=types.HttpRetryOptions(attempts=2),
          ),
      )

  def filter_entry(
      self,
      symbol: str,
      indicators: dict[str, Any],
      technical_reason: str,
  ) -> AIFilterResult:
    if not self.enabled:
      return AIFilterResult(
          decision="APROBAR",
          confidence=100,
          risk_multiplier=1.0,
          reasons=("Filtro Gemini desactivado; se usa la estrategia tecnica.",),
          model="disabled",
      )
    if self.client is None:
      return self._rejection("AI_ENABLED=true pero falta GEMINI_API_KEY.")

    prompt_payload = {
        "symbol": symbol,
        "timeframe": indicators.get("timeframe"),
        "technical_signal": "COMPRAR",
        "technical_reason": technical_reason,
        "market": indicators,
        "news_available": False,
    }
    prompt = (
        "Actua como filtro conservador de riesgo para una senal cuantitativa long-only. "
        "No inventes noticias. Decide APROBAR, RECHAZAR o REDUCIR_RIESGO. "
        "REDUCIR_RIESGO debe usar risk_multiplier entre 0.25 y 0.75; APROBAR usa 1.0. "
        "Evalua coherencia de tendencia, momentum y volatilidad de estos datos:\n"
        + json.dumps(prompt_payload, ensure_ascii=False, default=str)
    )
    schema = {
        "type": "object",
        "properties": {
            "decision": {
                "type": "string",
                "enum": ["APROBAR", "RECHAZAR", "REDUCIR_RIESGO"],
            },
            "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
            "risk_multiplier": {"type": "number", "minimum": 0, "maximum": 1},
            "reasons": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["decision", "confidence", "risk_multiplier", "reasons"],
    }

    last_error: Exception | None = None
    for _attempt in range(2):
      try:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2_048,
                response_mime_type="application/json",
                response_json_schema=schema,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.LOW
                ),
            ),
        )
        result = json.loads(response.text)
        decision = str(result["decision"]).upper()
        confidence = int(result["confidence"])
        risk_multiplier = float(result["risk_multiplier"])
        reasons = tuple(str(reason) for reason in result["reasons"])
        if decision not in {"APROBAR", "RECHAZAR", "REDUCIR_RIESGO"}:
          raise ValueError(f"Decision no permitida: {decision}")
        if not 0 <= confidence <= 100:
          raise ValueError("Confianza fuera de rango.")
        if decision == "APROBAR":
          risk_multiplier = 1.0
        elif decision == "RECHAZAR":
          risk_multiplier = 0.0
        else:
          risk_multiplier = min(max(risk_multiplier, 0.25), 0.75)
        if confidence < self.min_confidence:
          return self._rejection(
              f"Confianza Gemini {confidence} menor al minimo {self.min_confidence}."
          )
        return AIFilterResult(
            decision=decision,
            confidence=confidence,
            risk_multiplier=risk_multiplier,
            reasons=reasons,
            model=self.model_name,
        )
      except Exception as exc:
        last_error = exc
    return self._rejection(f"Fallo del filtro Gemini: {last_error}")

  def _rejection(self, message: str) -> AIFilterResult:
    return AIFilterResult(
        decision="RECHAZAR",
        confidence=0,
        risk_multiplier=0.0,
        reasons=(message,),
        model=self.model_name,
        error=message,
    )

  def analyze_market(
      self, symbol: str, indicators: dict[str, Any] | None = None, **_: Any
  ) -> dict[str, Any]:
    """Adaptador para integraciones antiguas; usa el nuevo filtro de entrada."""
    result = self.filter_entry(symbol, indicators or {}, "Senal tecnica externa")
    decision_map = {
        "APROBAR": "COMPRAR",
        "REDUCIR_RIESGO": "COMPRAR",
        "RECHAZAR": "MANTENER",
    }
    return {
        "decision": decision_map[result.decision],
        "confianza": result.confidence,
        "razon": "; ".join(result.reasons),
        "risk_multiplier": result.risk_multiplier,
    }
