"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.workflow.provider import AgentProvider
from app.workflow.provider_factory import get_agent_provider
from app.workflow.repository import WorkflowRepository, workflow_repository


def provider_dependency() -> AgentProvider:
    return get_agent_provider()


def repository_dependency() -> WorkflowRepository:
    return workflow_repository


SettingsDep = Annotated[Settings, Depends(get_settings)]
ProviderDep = Annotated[AgentProvider, Depends(provider_dependency)]
RepositoryDep = Annotated[WorkflowRepository, Depends(repository_dependency)]
