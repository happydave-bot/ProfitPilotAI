from __future__ import annotations

from core.models import MarketOffer, Product
from core.deal_scanner import DealScanner
from ui.dashboard import render_deals


def scan_product(query: str) -> str:
    """Run a deterministic local scan using the entered product query."""
    query = query.strip()
    if not query:
        return "Bitte ein Produkt eingeben."

    product = Product(title=query, brand="", ean=None)
    amazon = MarketOffer(source="amazon", price=40.0, url="https://example.com/amazon")
    ebay = MarketOffer(source="ebay", price=75.0, url="https://example.com/ebay")
    candidate = Product(title=query, brand="", ean=None)
    deals = DealScanner.scan(
        product,
        amazon,
        [(candidate, ebay)],
        ebay_fee_percent=12.9,
        packaging_cost=2.0,
    )
    return render_deals(deals)


def run_search() -> None:
    print("ProfitPilotAI – Deal Scanner")
    print("============================")
    query = input("Produkt suchen: ")
    print()
    print(scan_product(query))


if __name__ == "__main__":
    run_search()
