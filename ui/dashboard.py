from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from core.deal_scanner import ScanCandidate


def render_deals(candidates: Iterable[ScanCandidate]) -> str:
    """Render ranked deals as a compact terminal-friendly dashboard."""
    rows = []
    for index, candidate in enumerate(candidates, start=1):
        deal = candidate.deal
        rows.append(
            f"{index:>2}. {candidate.product.title} | "
            f"Amazon {candidate.amazon.price:.2f} EUR | "
            f"eBay {candidate.ebay.price:.2f} EUR | "
            f"Profit {deal.profit:.2f} EUR | ROI {deal.roi:.1f}% | "
            f"Match {candidate.match_confidence:.1f}%"
        )
    return "\n".join(rows) if rows else "Keine Deals gefunden."


def deal_to_dict(candidate: ScanCandidate) -> dict[str, object]:
    """Return a JSON-friendly representation for a future web UI."""
    deal = asdict(candidate.deal)
    return {
        "title": candidate.product.title,
        "match_confidence": candidate.match_confidence,
        "amazon_price": candidate.amazon.price,
        "ebay_price": candidate.ebay.price,
        **deal,
    }
