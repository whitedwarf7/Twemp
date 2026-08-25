"""Provider-neutral reasoning contract.

Orchestration code depends only on this protocol, so deterministic fixtures and live model
providers stay interchangeable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.workflow.catalog import AgentDefinition
from app.workflow.schemas import (
    AgentFinding,
    IncidentInput,
    IncidentOutcome,
    ProviderMode,
    RemediationPlan,
    TeamReport,
    VerificationReport,
)


@dataclass(frozen=True)
class SpecialistTask:
    run_id: str
    agent: AgentDefinition
    incident: IncidentInput
    objective: str
    prior_findings: tuple[AgentFinding, ...]
    team_reports: tuple[TeamReport, ...]
    plan: RemediationPlan | None


@dataclass(frozen=True)
class TeamSynthesisTask:
    run_id: str
    orchestrator: AgentDefinition
    incident: IncidentInput
    findings: tuple[AgentFinding, ...]
    prior_reports: tuple[TeamReport, ...]


@dataclass(frozen=True)
class PlanTask:
    run_id: str
    orchestrator: AgentDefinition
    incident: IncidentInput
    findings: tuple[AgentFinding, ...]
    reports: tuple[TeamReport, ...]


@dataclass(frozen=True)
class VerificationTask:
    run_id: str
    agent: AgentDefinition
    incident: IncidentInput
    plan: RemediationPlan
    findings: tuple[AgentFinding, ...]


@dataclass(frozen=True)
class ClosureTask:
    run_id: str
    agent: AgentDefinition
    incident: IncidentInput
    plan: RemediationPlan
    verification: VerificationReport
    findings: tuple[AgentFinding, ...]
    reports: tuple[TeamReport, ...]


@runtime_checkable
class AgentProvider(Protocol):
    """Bounded reasoning operations available to the orchestration engine."""

    @property
    def mode(self) -> ProviderMode: ...

    async def run_specialist(self, task: SpecialistTask) -> AgentFinding: ...

    async def synthesize_team(self, task: TeamSynthesisTask) -> TeamReport: ...

    async def draft_plan(self, task: PlanTask) -> RemediationPlan: ...

    async def verify_recovery(self, task: VerificationTask) -> VerificationReport: ...

    async def close_incident(self, task: ClosureTask) -> IncidentOutcome: ...
