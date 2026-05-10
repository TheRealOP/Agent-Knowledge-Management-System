from __future__ import annotations

import datetime
import json
from pathlib import Path


class TokenTracker:
    def __init__(self, log_path: str) -> None:
        self._log_path = Path(log_path)

    def log(self, provider: str, model: str, tokens: int, cost_usd: float) -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "provider": provider,
            "model": model,
            "tokens": tokens,
            "cost_usd": cost_usd,
            "date": datetime.date.today().isoformat(),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        with self._log_path.open("a") as f:
            f.write(json.dumps(record) + "\n")

    def load_today(self) -> list[dict]:
        today = datetime.date.today().isoformat()
        return [r for r in self.load_all() if r.get("date") == today]

    def load_all(self) -> list[dict]:
        if not self._log_path.exists():
            return []
        records = []
        with self._log_path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
