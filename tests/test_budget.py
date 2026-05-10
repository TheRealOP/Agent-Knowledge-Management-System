from __future__ import annotations

import pytest

from akms.core.budget import BudgetTracker


def test_record_usage_daily_total(tmp_dir):
    """record_usage then daily_total_usd returns the recorded cost."""
    tracker = BudgetTracker()
    tracker.record_usage("claude", "sonnet", 100, 50, 0.01)
    assert abs(tracker.daily_total_usd() - 0.01) < 1e-9


def test_multiple_records_sum(tmp_dir):
    """Multiple records: daily_total_usd returns their sum."""
    tracker = BudgetTracker()
    tracker.record_usage("claude", "sonnet", 100, 50, 0.01)
    tracker.record_usage("openai", "gpt-4", 200, 100, 0.02)
    assert abs(tracker.daily_total_usd() - 0.03) < 1e-9


def test_is_over_limit_true(tmp_dir):
    """is_over_limit returns True when total >= limit."""
    tracker = BudgetTracker()
    tracker.record_usage("claude", "sonnet", 100, 50, 0.01)
    assert tracker.is_over_limit(0.005) is True


def test_is_over_limit_false(tmp_dir):
    """is_over_limit returns False when total < limit."""
    tracker = BudgetTracker()
    tracker.record_usage("claude", "sonnet", 100, 50, 0.01)
    assert tracker.is_over_limit(1.0) is False


def test_should_warn_true(tmp_dir):
    """should_warn returns True when any single record cost_usd >= warn threshold."""
    tracker = BudgetTracker()
    tracker.record_usage("claude", "sonnet", 100, 50, 0.01)
    assert tracker.should_warn(0.01) is True


def test_should_warn_false(tmp_dir):
    """should_warn returns False when no record cost >= warn threshold."""
    tracker = BudgetTracker()
    tracker.record_usage("claude", "sonnet", 100, 50, 0.01)
    assert tracker.should_warn(1.0) is False


def test_summary_keys(tmp_dir):
    """summary() dict has keys: today_usd, total_usd, record_count, by_provider."""
    tracker = BudgetTracker()
    tracker.record_usage("claude", "sonnet", 100, 50, 0.01)
    tracker.record_usage("openai", "gpt-4", 200, 100, 0.02)

    s = tracker.summary()
    assert "today_usd" in s
    assert "total_usd" in s
    assert "record_count" in s
    assert "by_provider" in s
    assert s["record_count"] == 2
    assert abs(s["total_usd"] - 0.03) < 1e-9
    assert "claude" in s["by_provider"]
    assert "openai" in s["by_provider"]
