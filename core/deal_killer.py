from core.models import DealResult, Decision, MarketOffer


class DealKillerEngine:
    """Hard-stop checks that prevent risky deals from reaching BUY."""

    MAX_EBAY_COMPETITION = 25
    MIN_PROFIT = 10.0
    MAX_PRICE_DROP_PERCENT = -8.0
    MIN_DEMAND_SCORE = 35.0
    MAX_RETURN_RATE_PERCENT = 15.0

    @classmethod
    def evaluate(cls, result: DealResult, amazon: MarketOffer, ebay: MarketOffer) -> DealResult:
        if result.decision is Decision.IGNORE:
            return result

        if amazon.seller.strip().lower() in {"amazon", "amazon.de", "amazon eu"}:
            return cls._reject(result, "Amazon verkauft das Produkt selbst")

        if ebay.competition_count is not None and ebay.competition_count > cls.MAX_EBAY_COMPETITION:
            return cls._reject(result, "Zu viele eBay-Angebote")

        if result.profit < cls.MIN_PROFIT:
            return cls._reject(result, "Gewinn unter Mindestziel")

        if ebay.price_trend_percent is not None and ebay.price_trend_percent <= cls.MAX_PRICE_DROP_PERCENT:
            return cls._reject(result, "Verkaufspreis fällt deutlich")

        if ebay.demand_score is not None and ebay.demand_score < cls.MIN_DEMAND_SCORE:
            return cls._reject(result, "Nachfrage zu niedrig")

        if ebay.return_rate_percent is not None and ebay.return_rate_percent > cls.MAX_RETURN_RATE_PERCENT:
            return cls._reject(result, "Retourenrisiko zu hoch")

        return result

    @staticmethod
    def _reject(result: DealResult, reason: str) -> DealResult:
        return DealResult(
            profit=result.profit,
            roi=result.roi,
            score=result.score,
            decision=Decision.IGNORE,
            reason=reason,
        )
