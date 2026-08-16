from core.models import DealResult, Decision


class DecisionEngine:
    @staticmethod
    def decide(result: DealResult) -> DealResult:
        if result.decision is Decision.IGNORE:
            return result
        if result.score >= 80:
            return result
        return DealResult(
            profit=result.profit,
            roi=result.roi,
            score=result.score,
            decision=Decision.WATCH,
            reason="Score unter Kauf-Schwelle",
        )
