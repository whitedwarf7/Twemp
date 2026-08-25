"""Runtime and transport contracts for the Twemp incident workflow.

The JSON contract is camelCase so the existing frontend consumes this API unchanged.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
)
from pydantic.alias_generators import to_camel

Severity = Literal["SEV-1", "SEV-2", "SEV-3"]
Team = Literal["command", "triage", "investigation", "response", "communications"]
OperationalTeam = Literal["triage", "investigation", "response", "communications"]
AgentRole = Literal["main-orchestrator", "sub-orchestrator", "specialist"]
AgentStatus = Literal["queued", "running", "completed", "blocked", "cancelled", "failed"]
FindingSeverity = Literal["info", "warning", "critical"]
RiskLevel = Literal["low", "medium", "high"]
EventLevel = Literal["neutral", "success", "warning", "critical"]
ApprovalStatus = Literal["pending", "approved", "rejected"]
CheckStatus = Literal["passed", "failed"]
ProviderMode = Literal["demo", "openai"]

WorkflowPhase = Literal[
    "intake",
    "triage",
    "investigation",
    "planning",
    "approval",
    "remediation",
    "verification",
    "resolved",
    "rejected",
    "failed",
]

WorkflowStatus = Literal["running", "awaiting_approval", "completed", "rejected", "failed"]

WorkflowEventType = Literal[
    "workflow-started",
    "delegation",
    "agent-started",
    "finding",
    "synthesis",
    "plan-ready",
    "approval-requested",
    "approval-granted",
    "approval-rejected",
    "remediation",
    "verification",
    "communication",
    "workflow-completed",
    "workflow-failed",
]


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC value."""
    return datetime.now(UTC)


def _to_iso_z(value: datetime) -> str:
    """Serialize to the ISO-8601 `Z` form the frontend contract expects."""
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


Timestamp = Annotated[AwareDatetime, PlainSerializer(_to_iso_z, return_type=str, when_used="json")]

Identifier = Annotated[str, StringConstraints(min_length=1)]
Confidence = Annotated[float, Field(ge=0, le=1)]
Headline = Annotated[str, StringConstraints(min_length=3, max_length=160)]


class ContractModel(BaseModel):
    """Base model that serializes camelCase, rejects unknown keys, and validates mutations."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        validate_assignment=True,
    )


Signal = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=240)]


class IncidentInput(ContractModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=120)]
    description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=20, max_length=2000)
    ]
    service: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=2,
            max_length=80,
            pattern=r"^[A-Za-z0-9._/-]+$",
        ),
    ]
    severity: Severity
    region: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
    signals: Annotated[list[Signal], Field(min_length=1, max_length=12)]


class AgentRuntime(ContractModel):
    id: Identifier
    name: Identifier
    short_name: Identifier
    role: AgentRole
    team: Team
    parent_id: Identifier | None
    mission: Identifier
    capabilities: Annotated[list[Identifier], Field(min_length=1)]
    status: AgentStatus
    current_task: str | None
    output_summary: str | None
    started_at: Timestamp | None
    completed_at: Timestamp | None


class AgentFinding(ContractModel):
    id: Identifier
    agent_id: Identifier
    team: Team
    headline: Headline
    detail: Annotated[str, StringConstraints(min_length=10, max_length=1200)]
    evidence: Annotated[
        list[Annotated[str, StringConstraints(min_length=3, max_length=320)]],
        Field(min_length=1, max_length=8),
    ]
    confidence: Confidence
    severity: FindingSeverity


class TeamReport(ContractModel):
    id: Identifier
    orchestrator_id: Identifier
    team: Team
    title: Headline
    summary: Annotated[str, StringConstraints(min_length=10, max_length=1500)]
    key_findings: Annotated[
        list[Annotated[str, StringConstraints(min_length=3, max_length=300)]],
        Field(min_length=1, max_length=8),
    ]
    recommendation: Annotated[str, StringConstraints(min_length=5, max_length=800)]
    confidence: Confidence


class RemediationAction(ContractModel):
    id: Identifier
    title: Headline
    detail: Annotated[str, StringConstraints(min_length=10, max_length=800)]
    owner_agent_id: Identifier
    risk: RiskLevel
    reversible: bool
    expected_signal: Annotated[str, StringConstraints(min_length=5, max_length=400)]


class RemediationPlan(ContractModel):
    id: Identifier
    hypothesis: Annotated[str, StringConstraints(min_length=10, max_length=1000)]
    summary: Annotated[str, StringConstraints(min_length=10, max_length=1000)]
    risk_level: RiskLevel
    blast_radius: Annotated[str, StringConstraints(min_length=5, max_length=500)]
    actions: Annotated[list[RemediationAction], Field(min_length=1, max_length=8)]
    rollback: Annotated[str, StringConstraints(min_length=10, max_length=800)]
    validation_checks: Annotated[
        list[Annotated[str, StringConstraints(min_length=5, max_length=320)]],
        Field(min_length=1, max_length=10),
    ]


class ApprovalRequest(ContractModel):
    id: Identifier
    status: ApprovalStatus
    requested_at: Timestamp
    decided_at: Timestamp | None
    decided_by: str | None
    note: str | None
    plan: RemediationPlan


class VerificationCheck(ContractModel):
    label: Headline
    value: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    status: CheckStatus
    detail: Annotated[str, StringConstraints(min_length=3, max_length=400)]


class VerificationReport(ContractModel):
    status: CheckStatus
    summary: Annotated[str, StringConstraints(min_length=10, max_length=1000)]
    checks: Annotated[list[VerificationCheck], Field(min_length=1, max_length=10)]


class IncidentOutcome(ContractModel):
    root_cause: Annotated[str, StringConstraints(min_length=10, max_length=1000)]
    resolution: Annotated[str, StringConstraints(min_length=10, max_length=1000)]
    customer_impact: Annotated[str, StringConstraints(min_length=10, max_length=800)]
    follow_ups: Annotated[
        list[Annotated[str, StringConstraints(min_length=5, max_length=320)]],
        Field(min_length=1, max_length=10),
    ]


class WorkflowEvent(ContractModel):
    id: Identifier
    sequence: Annotated[int, Field(gt=0)]
    timestamp: Timestamp
    type: WorkflowEventType
    phase: WorkflowPhase
    actor_id: Identifier
    actor_name: Identifier
    team: Team
    title: Headline
    detail: Annotated[str, StringConstraints(min_length=3, max_length=1200)]
    level: EventLevel


class WorkflowMetrics(ContractModel):
    agents_total: Annotated[int, Field(ge=0)]
    agents_completed: Annotated[int, Field(ge=0)]
    active_agents: Annotated[int, Field(ge=0)]
    tasks_completed: Annotated[int, Field(ge=0)]
    handoffs: Annotated[int, Field(ge=0)]
    confidence: Confidence


class WorkflowRun(ContractModel):
    id: Identifier
    incident: IncidentInput
    mode: ProviderMode
    status: WorkflowStatus
    phase: WorkflowPhase
    started_at: Timestamp
    updated_at: Timestamp
    agents: list[AgentRuntime]
    events: list[WorkflowEvent]
    findings: list[AgentFinding]
    team_reports: list[TeamReport]
    plan: RemediationPlan | None
    approval: ApprovalRequest | None
    verification: VerificationReport | None
    outcome: IncidentOutcome | None
    metrics: WorkflowMetrics


class ApprovalDecision(ContractModel):
    decision: Literal["approve", "reject"]
    reviewer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""


class ApiError(BaseModel):
    error: str
    details: list[str] | None = None


DEFAULT_INCIDENT = IncidentInput(
    title="Checkout latency surge across EU region",
    description=(
        "Checkout p95 latency climbed from 420 ms to 8.4 s shortly after the payment-router "
        "deployment. Error rate is 18% in eu-central and the retry queue continues to grow."
    ),
    service="payment-router",
    severity="SEV-1",
    region="eu-central",
    signals=[
        "p95 latency 8.4 s (baseline 420 ms)",
        "HTTP 5xx rate 18%",
        "payment retry queue 4.7x above baseline",
    ],
)
