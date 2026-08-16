from __future__ import annotations

from core.deal_scanner import DealScanner
from core.models import MarketOffer, Product
from ui.dashboard import render_deals


def run() -> None:
    """Run the local ProfitPilotAI demo application."""
    print("ProfitPilotAI Dashboard")
    print("=" * 24)
    print(run_demo())


def run_demo() -> str:
    """Run a deterministic UI demo until live credentials are configured."""
    product = Product(title="Demo Product", brand="Demo", ean="4000000000000")
    amazon = MarketOffer(source="amazon", price=40.0, url="https://example.com/amazon")
    ebay = MarketOffer(source="ebay", price=75.0, url="https://example.com/ebay")
    candidate_product = Product(title="Demo Product", brand="Demo", ean="4000000000000")
    candidates = DealScanner.scan(
        product,
        amazon,
        [(candidate_product, ebay)],
        ebay_fee_percent=12.9,
        packaging_cost=2.0,
    )
    return render_deals(candidates)


if __name__ == "__main__":
    run()
