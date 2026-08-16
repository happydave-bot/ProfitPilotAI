from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    BUY = "KAUFEN"
    WATCH = "BEOBACHTEN"
    IGNORE = "IGNORIEREN"


@dataclass(frozen=True, slots=True)
class Product:
    title: str
    brand: str = ""
    asin: str | None = None
    ean: str | None = None
    model: str | None = None


@dataclass(frozen=True, slots=True)
class MarketOffer:
    source: str
    url: str
    price: float
    shipping: float = 0.0
    seller: str = ""
    competition_count: int | None = None
    price_trend_percent: float | None = None
    demand_score: float | None = None
    return_rate_percent: float | None = None


@dataclass(frozen=True, slots=True)
class DealInput:
    product: Product
    amazon: MarketOffer
    ebay: MarketOffer
    ebay_fee_percent: float
    packaging_cost: float = 0.0


@dataclass(frozen=True, slots=True)
class DealResult:
    profit: float
    roi: float
    score: int
    decision: Decision
    reason: str
