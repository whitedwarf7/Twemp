"""Selects the reasoning provider without importing optional dependencies eagerly."""

from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings
from app.workflow.provider import AgentProvider


def build_agent_provider(settings: Settings) -> AgentProvider:
    if settings.agent_provider == "demo":
        from app.workflow.demo_provider import DemoAgentProvider

        return DemoAgentProvider()

    from app.workflow.openai_provider import OpenAIAgentProvider

    return OpenAIAgentProvider(settings)


@lru_cache(maxsize=1)
def get_agent_provider() -> AgentProvider:
    return build_agent_provider(get_settings())
