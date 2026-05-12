"""Advanced orchestrator with multi-provider load balancing and quota awareness."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from akms.core.orchestrator import Orchestrator

if TYPE_CHECKING:
    from akms.config import AKMSConfig
    from akms.core.quota import QuotaManager
    from akms.knowledge.graph import HybridGraph
    from akms.providers.registry import ProviderRegistry


class MultiProviderOrchestrator(Orchestrator):
    """Orchestrator that balances across pools of providers using a QuotaManager."""

    def __init__(
        self,
        config: AKMSConfig,
        registry: ProviderRegistry,
        graph: HybridGraph,
        quota_manager: QuotaManager,
    ) -> None:
        super().__init__(config, registry, graph)
        self._quota_manager = quota_manager

    def _build_provider(self, role: str) -> tuple[Any, str]:
        """Override to check agent_pools first, then fallback to agent_assignments."""
        pool = self._config.agent_pools.get(role)
        
        if pool and pool.assignments:
            # Select the best one from the pool based on health/usage
            candidates = [(a.provider, a.model) for a in pool.assignments]
            provider_name, model = self._quota_manager.select_best_provider(role, candidates)
        else:
            # Fallback to standard single assignment
            assignment = self._config.agent_assignments.get(role)
            if assignment is None:
                raise ValueError(f"No agent assignment or pool configured for role '{role}'")
            provider_name, model = assignment.provider, assignment.model

        provider_cfg = self._config.providers.get(provider_name)
        if provider_cfg is None:
            raise ValueError(f"Provider '{provider_name}' not found in config")
        
        provider = self._registry.create_from_config(provider_name, provider_cfg)
        
        # Wrap the provider to record usage automatically
        return self._wrap_provider(provider, provider_name, model), model

    def _wrap_provider(self, provider: Any, name: str, model: str) -> Any:
        """Monkey-patch or wrap the provider to intercept chat calls for usage tracking."""
        original_chat = provider.chat
        quota_manager = self._quota_manager

        def tracked_chat(*args: Any, **kwargs: Any) -> Any:
            response = original_chat(*args, **kwargs)
            # Record usage (simple increment for messages, plus tokens if available)
            quota_manager.record_usage(
                provider=name,
                model=model,
                tokens_input=response.usage.get("prompt_tokens", 0) if hasattr(response, "usage") else 0,
                tokens_output=response.usage.get("completion_tokens", 0) if hasattr(response, "usage") else 0,
                messages_inc=1
            )
            return response

        provider.chat = tracked_chat
        return provider
