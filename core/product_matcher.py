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
    def _title_similarity(cls, left: str, right: str) -> float:
        left_norm = cls._norm(left)
        right_norm = cls._norm(right)
        sequence_score = cls._similarity(left_norm, right_norm)
        left_tokens = set(left_norm.split())
        right_tokens = set(right_norm.split())
        if not left_tokens or not right_tokens:
            return sequence_score
        overlap = len(left_tokens & right_tokens) / len(left_tokens | right_tokens) * 100
        return max(sequence_score, overlap)

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

        title_score = cls._title_similarity(left.title, right.title)
        brand_score = cls._similarity(left.brand, right.brand) if left.brand and right.brand else 0.0
        model_score = cls._similarity(left.model, right.model) if left.model and right.model else 0.0

        weighted = title_score * 0.55 + brand_score * 0.25 + model_score * 0.20

        title_tokens_left = set(cls._norm(left.title).split())
        title_tokens_right = set(cls._norm(right.title).split())
        shared_ratio = (
            len(title_tokens_left & title_tokens_right)
            / len(title_tokens_left | title_tokens_right)
            if title_tokens_left and title_tokens_right
            else 0.0
        )
        strong_brand_title_match = brand_score >= 99 and shared_ratio >= 0.60

        if brand_score >= 99:
            reasons.append("Marke stimmt überein")
        if model_score >= 99:
            reasons.append("Modell stimmt überein")
        if title_score >= 85:
            reasons.append("Produkttitel ist sehr ähnlich")
        if strong_brand_title_match:
            reasons.append("Produkttitel enthält die wesentlichen gemeinsamen Produktbegriffe")

        matched = weighted >= cls.MIN_MATCH or strong_brand_title_match
        confidence = max(weighted, 95.0) if strong_brand_title_match else weighted
        return MatchResult(round(confidence, 2), matched, tuple(reasons))
