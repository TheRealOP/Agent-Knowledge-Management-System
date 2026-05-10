from __future__ import annotations

import pytest

from akms.providers.base import LLMProvider
from akms.providers.registry import ProviderRegistry, build_default_registry
from akms.core.message import Message, Response


class StubProvider(LLMProvider):
    provider_name = "stub"

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def chat(self, messages, model=None, **kwargs):
        ...

    def stream(self, messages, model=None, **kwargs):
        return iter([])

    def count_tokens(self, messages):
        return 0

    def _to_provider_format(self, messages):
        return []

    def _from_provider_response(self, raw, model):
        ...


def test_register_and_available():
    """register('foo', SomeClass) then available() returns ['foo']."""
    registry = ProviderRegistry()
    registry.register("foo", StubProvider)
    assert registry.available() == ["foo"]


def test_create_returns_instance():
    """create('foo', **kwargs) calls SomeClass(**kwargs) and returns instance."""
    registry = ProviderRegistry()
    registry.register("foo", StubProvider)
    instance = registry.create("foo", some_kwarg="val")
    assert isinstance(instance, StubProvider)
    assert instance.kwargs == {"some_kwarg": "val"}


def test_create_unknown_raises_value_error():
    """create('unknown') raises ValueError with 'Unknown provider' in message."""
    registry = ProviderRegistry()
    with pytest.raises(ValueError, match="Unknown provider"):
        registry.create("unknown")


def test_build_default_registry_contains_claude_and_openai():
    """build_default_registry().available() contains at least ['claude', 'openai']."""
    registry = build_default_registry()
    available = registry.available()
    assert "claude" in available
    assert "openai" in available
