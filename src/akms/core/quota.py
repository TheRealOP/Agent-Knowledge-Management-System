"""Quota and usage management for multi-provider orchestration."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from akms.knowledge.db import SQLiteLayer


class QuotaManager:
    """Tracks and balances usage across multiple providers."""

    def __init__(self, db: SQLiteLayer) -> None:
        self._db = db

    def record_usage(
        self,
        provider: str,
        model: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        messages_inc: int = 1,
    ) -> None:
        """Update usage stats in the DB."""
        self._db.update_usage(
            provider=provider,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            messages_inc=messages_inc,
        )

    def get_provider_health(self) -> dict[str, dict[str, Any]]:
        """Return a map of provider/model to their current health (usage vs quota)."""
        all_usage = self._db.get_all_usage()
        health = {}
        for entry in all_usage:
            key = f"{entry['provider']}/{entry['model']}"
            
            # Simple health score: 1.0 = unused, 0.0 = exhausted
            usage_val = 0
            if entry['quota_type'] == 'messages':
                usage_val = entry['messages_count']
            else:
                usage_val = entry['tokens_input'] + entry['tokens_output']
                
            limit = entry['quota_limit']
            score = 1.0 - (usage_val / limit) if limit > 0 else 1.0
            
            health[key] = {
                "score": max(0.0, score),
                "usage": usage_val,
                "limit": limit,
                "type": entry['quota_type']
            }
        return health

    def select_best_provider(self, role: str, assignments: list[tuple[str, str]]) -> tuple[str, str]:
        """
        Select the best provider from a list of candidates based on health.
        If all candidates are unhealthy, it returns the one with the highest score.
        """
        health = self.get_provider_health()
        
        candidates = []
        for p_name, model in assignments:
            key = f"{p_name}/{model}"
            h = health.get(key, {"score": 1.0})
            candidates.append((p_name, model, h["score"]))
            
        # Sort by health score descending (healthiest first)
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates[0][0], candidates[0][1]
