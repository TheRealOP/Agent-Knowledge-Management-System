from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any


@dataclass
class UsageRecord:
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    date: str
    timestamp: str


class BudgetTracker:
    def __init__(self) -> None:
        self._records: list[UsageRecord] = []

    def record_usage(self, provider: str, model: str, tokens_in: int, tokens_out: int, cost_usd: float) -> None:
        self._records.append(
            UsageRecord(
                provider=provider,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                date=datetime.date.today().isoformat(),
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
        )

    def daily_total_usd(self, date: str | None = None) -> float:
        target = date if date is not None else datetime.date.today().isoformat()
        return sum(r.cost_usd for r in self._records if r.date == target)

    def is_over_limit(self, limit_usd: float) -> bool:
        return self.daily_total_usd() >= limit_usd

    def should_warn(self, warn_usd: float) -> bool:
        return any(r.cost_usd >= warn_usd for r in self._records)

    def summary(self) -> dict[str, Any]:
        by_provider: dict[str, float] = {}
        for r in self._records:
            by_provider[r.provider] = by_provider.get(r.provider, 0.0) + r.cost_usd
        return {
            "today_usd": self.daily_total_usd(),
            "total_usd": sum(r.cost_usd for r in self._records),
            "record_count": len(self._records),
            "by_provider": by_provider,
        }
