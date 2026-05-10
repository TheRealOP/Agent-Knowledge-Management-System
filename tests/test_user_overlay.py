from __future__ import annotations

import json
import pytest

from akms.knowledge.user_overlay import UserOverlay


def test_set_get(tmp_path):
    uo = UserOverlay(str(tmp_path / "overlay"))
    uo.set_concept("python", 0.8, "Know it well")
    data = uo.get_concept("python")
    assert data is not None
    assert abs(data["understanding"] - 0.8) < 1e-9
    assert data["notes"] == "Know it well"


def test_list(tmp_path):
    uo = UserOverlay(str(tmp_path / "overlay"))
    uo.set_concept("python", 0.8)
    uo.set_concept("rust", 0.3)
    concepts = uo.list_concepts()
    assert "python" in concepts
    assert "rust" in concepts


def test_remove(tmp_path):
    uo = UserOverlay(str(tmp_path / "overlay"))
    uo.set_concept("python", 0.8)
    removed = uo.remove_concept("python")
    assert removed is True
    assert uo.get_concept("python") is None


def test_remove_nonexistent(tmp_path):
    uo = UserOverlay(str(tmp_path / "overlay"))
    removed = uo.remove_concept("nonexistent")
    assert removed is False


def test_missing_file_empty(tmp_path):
    uo = UserOverlay(str(tmp_path / "overlay"))
    concepts = uo.list_concepts()
    assert concepts == {}


def test_understanding_clamped(tmp_path):
    uo = UserOverlay(str(tmp_path / "overlay"))
    uo.set_concept("over", 1.5)
    uo.set_concept("under", -0.5)
    assert uo.get_concept("over")["understanding"] == 1.0
    assert uo.get_concept("under")["understanding"] == 0.0
