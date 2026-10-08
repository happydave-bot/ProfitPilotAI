from core.models import DealInput, DealResult, Decision


class ProfitEngine:
    MIN_PROFIT = 20.0
    MIN_ROI = 25.0
    EBAY_FIXED_ORDER_FEE_UNDER_OR_EQUAL_10 = 0.35
    EBAY_FIXED_ORDER_FEE_OVER_10 = 0.45

    @classmethod
    def calculate(cls, data: DealInput) -> DealResult:
        if data.amazon.price <= 0:
            raise ValueError("Amazon price must be greater than zero")
        if data.ebay.price < 0 or data.amazon.shipping < 0 or data.ebay.shipping < 0:
            raise ValueError("Prices and shipping costs cannot be negative")
        if data.ebay_fee_percent < 0 or data.packaging_cost < 0:
            raise ValueError("Fees and packaging cost cannot be negative")

        ebay_fee_base = data.ebay.price + data.ebay.shipping
        ebay_fee = ebay_fee_base * data.ebay_fee_percent / 100
        fixed_order_fee = (
            cls.EBAY_FIXED_ORDER_FEE_OVER_10
            if ebay_fee_base > 10.0
            else cls.EBAY_FIXED_ORDER_FEE_UNDER_OR_EQUAL_10
        )
        total_cost = (
            data.amazon.price
            + data.amazon.shipping
            + ebay_fee
            + fixed_order_fee
            + data.ebay.shipping
            + data.packaging_cost
        )
        profit = data.ebay.price - total_cost
        roi = profit / data.amazon.price * 100

        if profit < cls.MIN_PROFIT:
            decision = Decision.IGNORE
            reason = "Gewinn unter Mindestgewinn"
            score = max(0, min(100, int(profit * 2)))
        elif roi < cls.MIN_ROI:
            decision = Decision.IGNORE
            reason = "ROI unter Mindestwert"
            score = max(0, min(100, int(roi)))
        else:
            decision = Decision.BUY
            reason = "Profitabler Deal"
            score = max(0, min(100, int((profit * 2 + roi) / 2)))

        return DealResult(
            profit=round(profit, 2),
            roi=round(roi, 2),
            score=score,
            decision=decision,
            reason=reason,
        )
