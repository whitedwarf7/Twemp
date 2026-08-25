"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import provider_dependency, repository_dependency
from app.main import app
from app.workflow.demo_provider import DemoAgentProvider
from app.workflow.engine import decide_workflow, start_workflow
from app.workflow.provider import AgentProvider
from app.workflow.repository import WorkflowRepository
from app.workflow.schemas import DEFAULT_INCIDENT, ApprovalDecision, WorkflowRun


@pytest.fixture
def provider() -> AgentProvider:
    return DemoAgentProvider()


@pytest.fixture
def repository() -> WorkflowRepository:
    return WorkflowRepository()


@pytest.fixture
def client(provider: AgentProvider, repository: WorkflowRepository) -> Iterator[TestClient]:
    app.dependency_overrides[provider_dependency] = lambda: provider
    app.dependency_overrides[repository_dependency] = lambda: repository
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
async def pending_run(provider: AgentProvider) -> WorkflowRun:
    """A run that has executed every phase up to the human approval gate."""
    return await start_workflow(DEFAULT_INCIDENT, provider)


@pytest.fixture
async def completed_run(pending_run: WorkflowRun, provider: AgentProvider) -> WorkflowRun:
    return await decide_workflow(
        pending_run,
        ApprovalDecision(decision="approve", reviewer="Primary on-call", note="Reviewed"),
        provider,
    )


@pytest.fixture
async def rejected_run(pending_run: WorkflowRun, provider: AgentProvider) -> WorkflowRun:
    return await decide_workflow(
        pending_run,
        ApprovalDecision(decision="reject", reviewer="Incident commander", note="Too broad"),
        provider,
    )
