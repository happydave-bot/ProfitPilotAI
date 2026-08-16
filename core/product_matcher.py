from __future__ import annotations

from dataclasses import dataclass
import re
from difflib import SequenceMatcher

from core.models import Product


@dataclass(frozen=True, slots=True)
class MatchResult:
    score: float
    matched: bool
    reasons: tuple[str, ...]

    @property
    def is_match(self) -> bool:
        return self.matched

    @property
    def confidence(self) -> float:
        return self.score


class ProductMatcher:
    MIN_MATCH = 70.0

    @staticmethod
    def _norm(value: str | None) -> str:
        if not value:
            return ""
        value = value.lower().strip()
        return re.sub(r"[^a-z0-9äöüß]+", " ", value).strip()

    @classmethod
    def _similarity(cls, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        return SequenceMatcher(None, left, right).ratio() * 100

    @classmethod
    def match(cls, left: Product, right: Product) -> MatchResult:
        reasons: list[str] = []

        if left.ean and right.ean:
            if cls._norm(left.ean) == cls._norm(right.ean):
                return MatchResult(100.0, True, ("EAN stimmt überein",))
            return MatchResult(0.0, False, ("EAN stimmt nicht überein",))

        if left.asin and right.asin:
            if cls._norm(left.asin) == cls._norm(right.asin):
                return MatchResult(100.0, True, ("ASIN stimmt überein",))
            return MatchResult(0.0, False, ("ASIN stimmt nicht überein",))

        title_score = cls._similarity(left.title, right.title)
        brand_score = cls._similarity(left.brand, right.brand) if left.brand and right.brand else 0.0
        model_score = cls._similarity(left.model, right.model) if left.model and right.model else 0.0

        weighted = title_score * 0.55 + brand_score * 0.25 + model_score * 0.20

        if brand_score >= 99:
            reasons.append("Marke stimmt überein")
        if model_score >= 99:
            reasons.append("Modell stimmt überein")
        if title_score >= 85:
            reasons.append("Produkttitel ist sehr ähnlich")

        matched = weighted >= cls.MIN_MATCH
        return MatchResult(round(weighted, 2), matched, tuple(reasons))
