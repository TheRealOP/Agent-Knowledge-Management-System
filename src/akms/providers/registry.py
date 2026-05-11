"""Provider registry — discovers, registers, and creates provider instances."""

from __future__ import annotations

from typing import Any

from akms.config import ProviderConfig
from akms.providers.base import LLMProvider


class ProviderRegistry:
    """Factory registry for LLM provider adapters."""

    def __init__(self) -> None:
        self._providers: dict[str, type[LLMProvider]] = {}

    def register(self, name: str, provider_cls: type[LLMProvider]) -> None:
        self._providers[name] = provider_cls

    def create(self, name: str, **kwargs: Any) -> LLMProvider:
        if name not in self._providers:
            available = ", ".join(self._providers.keys()) or "none"
            raise ValueError(f"Unknown provider '{name}'. Available: {available}")
        return self._providers[name](**kwargs)

    def create_from_config(self, name: str, provider_config: ProviderConfig) -> LLMProvider:
        kwargs: dict[str, Any] = {}
        if provider_config.api_key:
            kwargs["api_key"] = provider_config.api_key
        if provider_config.base_url:
            kwargs["base_url"] = provider_config.base_url
        kwargs["models"] = provider_config.models
        if provider_config.tmux_pane:
            kwargs["tmux_pane"] = provider_config.tmux_pane
        return self.create(name, **kwargs)

    def available(self) -> list[str]:
        return list(self._providers.keys())


def build_default_registry() -> ProviderRegistry:
    """Create a registry pre-loaded with all built-in providers."""
    registry = ProviderRegistry()

    try:
        from akms.providers.claude import ClaudeProvider
        registry.register("claude", ClaudeProvider)
    except ImportError:
        pass

    try:
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

    # CLI providers — auth via the CLI binary itself, no API key needed
    try:
        from akms.providers.cli_subprocess import CLISubprocessProvider
        registry.register(
            "claude_cli",
            lambda **kw: CLISubprocessProvider(cli_binary="claude", print_flag="-p", **kw),
        )
        registry.register(
            "codex_cli",
            lambda **kw: CLISubprocessProvider(cli_binary="codex", print_flag="exec", model_flag=None, **kw),
        )
        registry.register(
            "gemini_cli",
            lambda **kw: CLISubprocessProvider(cli_binary="gemini", print_flag="-p", **kw),
        )
    except ImportError:
        pass

    return registry
