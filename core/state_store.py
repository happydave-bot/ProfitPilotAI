from __future__ import annotations

import json
from pathlib import Path


class JsonStateStore:
    """Persist alert fingerprints so restarts do not repeat old alerts."""

    def __init__(self, path: str | Path = "data/alert_state.json") -> None:
        self.path = Path(path)

    def load(self) -> set[str]:
        if not self.path.exists():
            return set()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            fingerprints = data.get("seen", [])
            return {item for item in fingerprints if isinstance(item, str)}
        except (OSError, json.JSONDecodeError, AttributeError, TypeError):
            return set()

    def save(self, seen: set[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps({"seen": sorted(seen)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
