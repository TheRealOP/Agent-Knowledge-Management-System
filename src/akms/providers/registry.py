# edited by gemini
"""Provider registry — discovers, registers, and creates provider instances.

Usage:
    registry = ProviderRegistry()
    registry.register("claude", ClaudeProvider)
    provider = registry.create("claude", api_key="sk-...")
"""

from __future__ import annotations

from typing import Any

from akms.config import AKMSConfig, ProviderConfig
from akms.providers.base import LLMProvider


# edited by gemini — registry class
class ProviderRegistry:
    """Factory registry for LLM provider adapters."""

    def __init__(self) -> None:
        # edited by gemini — maps provider name to its class
        self._providers: dict[str, type[LLMProvider]] = {}

    # edited by gemini — register a provider class
    def register(self, name: str, provider_cls: type[LLMProvider]) -> None:
        """Register a provider adapter class by name."""
        self._providers[name] = provider_cls

    # edited by gemini — create a provider instance
    def create(self, name: str, **kwargs: Any) -> LLMProvider:
        """Create a provider instance by name."""
        if name not in self._providers:
            available = ", ".join(self._providers.keys()) or "none"
            raise ValueError(
                f"Unknown provider '{name}'. Available: {available}"
            )
        return self._providers[name](**kwargs)

    # edited by gemini — create from config
    def create_from_config(
        self, name: str, provider_config: ProviderConfig
    ) -> LLMProvider:
        """Create a provider from an AKMSConfig provider entry."""
        kwargs: dict[str, Any] = {}
        if provider_config.api_key:
            kwargs["api_key"] = provider_config.api_key
        if provider_config.base_url:
            kwargs["base_url"] = provider_config.base_url
        kwargs["models"] = provider_config.models
        return self.create(name, **kwargs)

    # edited by gemini — list registered providers
    def available(self) -> list[str]:
        """Return list of registered provider names."""
        return list(self._providers.keys())


# edited by gemini — auto-register built-in providers
def build_default_registry() -> ProviderRegistry:
    """Create a registry pre-loaded with all built-in providers."""
    registry = ProviderRegistry()

    # Lazy imports to avoid requiring all provider deps
    try:  # edited by gemini
        from akms.providers.claude import ClaudeProvider
        registry.register("claude", ClaudeProvider)
    except ImportError:
        pass

    try:  # edited by gemini
        from akms.providers.openai_provider import OpenAIProvider
        registry.register("openai", OpenAIProvider)
    except ImportError:
        pass

    try:
        from akms.providers.gemini import GeminiProvider
        registry.register("gemini", GeminiProvider)
    except ImportError:
        pass

    try:
        from akms.providers.deepseek import DeepSeekProvider
        registry.register("deepseek", DeepSeekProvider)
    except ImportError:
        pass

    try:
        from akms.providers.ollama import OllamaProvider
        registry.register("ollama", OllamaProvider)
    except ImportError:
        pass

    return registry
