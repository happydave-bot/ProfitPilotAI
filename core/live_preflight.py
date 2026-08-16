from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LivePreflight:
    ok: bool
    missing: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def summary(self) -> str:
        if self.ok:
            lines = ["LIVE PREFLIGHT: OK"]
        else:
            lines = ["LIVE PREFLIGHT: NICHT BEREIT"]
            if self.missing:
                lines.append("Fehlt: " + ", ".join(self.missing))
        for warning in self.warnings:
            lines.append("Warnung: " + warning)
        return "\n".join(lines)


def validate_live_environment() -> LivePreflight:
    missing: list[str] = []
    warnings: list[str] = []

    required = {
        "AMAZON_CREATORS_CLIENT_ID": os.getenv("AMAZON_CREATORS_CLIENT_ID", "").strip(),
        "AMAZON_CREATORS_CLIENT_SECRET": os.getenv("AMAZON_CREATORS_CLIENT_SECRET", "").strip(),
        "AMAZON_PARTNER_TAG": os.getenv("AMAZON_PARTNER_TAG", "").strip(),
        "EBAY_CLIENT_ID": os.getenv("EBAY_CLIENT_ID", "").strip(),
        "EBAY_CLIENT_SECRET": os.getenv("EBAY_CLIENT_SECRET", "").strip(),
    }
    missing.extend(name for name, value in required.items() if not value)

    if not os.getenv("PROFITPILOT_QUERY", "").strip() and not os.getenv("PROFITPILOT_QUERIES", "").strip():
        missing.append("PROFITPILOT_QUERY oder PROFITPILOT_QUERIES")

    try:
        fee = float(os.getenv("PROFITPILOT_EBAY_FEE_PERCENT", "12.9"))
        if not 0 <= fee < 100:
            warnings.append("PROFITPILOT_EBAY_FEE_PERCENT liegt außerhalb 0-99.")
    except ValueError:
        missing.append("PROFITPILOT_EBAY_FEE_PERCENT (Zahl)")

    try:
        packaging = float(os.getenv("PROFITPILOT_PACKAGING_COST", "2.0"))
        if packaging < 0:
            warnings.append("PROFITPILOT_PACKAGING_COST ist negativ.")
    except ValueError:
        missing.append("PROFITPILOT_PACKAGING_COST (Zahl)")

    if not os.getenv("PROFITPILOT_QUERIES", "").strip() and os.getenv("PROFITPILOT_QUERY", "").strip():
        warnings.append("Es wird genau ein Suchbegriff verwendet.")

    return LivePreflight(ok=not missing, missing=tuple(missing), warnings=tuple(warnings))
