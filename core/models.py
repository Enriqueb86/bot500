"""Modelos de dominio compartidos por estrategia, ejecucion y reportes."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Position:
  symbol: str
  entry_time: str
  entry_price: float
  size: float
  stop_loss: float
  take_profit: float
  entry_fee: float
  signal_candle: str = ""
  reason: str = ""
  confidence: int = 0

  @property
  def entry_notional(self) -> float:
    return self.entry_price * self.size

  def to_dict(self) -> dict[str, Any]:
    return asdict(self)

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> "Position":
    return cls(**data)


@dataclass(frozen=True)
class TechnicalSignal:
  action: str
  reason: str


@dataclass(frozen=True)
class AIFilterResult:
  decision: str
  confidence: int
  risk_multiplier: float
  reasons: tuple[str, ...]
  model: str
  prompt_version: str = "v1"
  error: str | None = None

  @property
  def approved(self) -> bool:
    return self.decision in {"APROBAR", "REDUCIR_RIESGO"}
