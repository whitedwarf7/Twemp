"""The static Twemp agent hierarchy: 1 commander, 4 orchestrators, 12 specialists."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.workflow.schemas import AgentRole, AgentRuntime, OperationalTeam, Team


@dataclass(frozen=True)
class AgentDefinition:
    id: str
    name: str
    short_name: str
    role: AgentRole
    team: Team
    parent_id: str | None
    mission: str
    capabilities: tuple[str, ...] = field(default=())


MAIN_ORCHESTRATOR_ID = "incident-commander"

TEAM_ORCHESTRATOR_IDS: dict[OperationalTeam, str] = {
    "triage": "triage-lead",
    "investigation": "investigation-lead",
    "response": "response-lead",
    "communications": "communications-lead",
}

AGENT_CATALOG: tuple[AgentDefinition, ...] = (
    AgentDefinition(
        id=MAIN_ORCHESTRATOR_ID,
        name="Incident Commander",
        short_name="Commander",
        role="main-orchestrator",
        team="command",
        parent_id=None,
        mission=(
            "Maintain global incident state, coordinate team leads, and enforce the human "
            "approval boundary."
        ),
        capabilities=("global synthesis", "priority control", "approval governance"),
    ),
    AgentDefinition(
        id="triage-lead",
        name="Triage Orchestrator",
        short_name="Triage",
        role="sub-orchestrator",
        team="triage",
        parent_id=MAIN_ORCHESTRATOR_ID,
        mission="Establish severity, scope, customer impact, and the first causal hypotheses.",
        capabilities=("scope control", "signal correlation", "severity assessment"),
    ),
    AgentDefinition(
        id="alert-correlator",
        name="Alert Correlator",
        short_name="Alerts",
        role="specialist",
        team="triage",
        parent_id="triage-lead",
        mission="Cluster related alerts and establish a reliable incident onset window.",
        capabilities=("alert clustering", "time-series alignment"),
    ),
    AgentDefinition(
        id="impact-analyst",
        name="Impact Analyst",
        short_name="Impact",
        role="specialist",
        team="triage",
        parent_id="triage-lead",
        mission="Quantify affected journeys, regions, and customer cohorts.",
        capabilities=("impact modeling", "severity scoring"),
    ),
    AgentDefinition(
        id="change-intelligence",
        name="Change Intelligence",
        short_name="Changes",
        role="specialist",
        team="triage",
        parent_id="triage-lead",
        mission=(
            "Correlate deployments, configuration changes, and feature flags with incident onset."
        ),
        capabilities=("change correlation", "release analysis"),
    ),
    AgentDefinition(
        id="investigation-lead",
        name="Investigation Orchestrator",
        short_name="Investigate",
        role="sub-orchestrator",
        team="investigation",
        parent_id=MAIN_ORCHESTRATOR_ID,
        mission=(
            "Direct evidence gathering and converge on the most defensible causal hypothesis."
        ),
        capabilities=("hypothesis ranking", "evidence synthesis", "causal analysis"),
    ),
    AgentDefinition(
        id="telemetry-analyst",
        name="Telemetry Analyst",
        short_name="Metrics",
        role="specialist",
        team="investigation",
        parent_id="investigation-lead",
        mission="Analyze golden signals, saturation, and regional metric divergence.",
        capabilities=("metrics analysis", "anomaly detection"),
    ),
    AgentDefinition(
        id="log-investigator",
        name="Log Investigator",
        short_name="Logs",
        role="specialist",
        team="investigation",
        parent_id="investigation-lead",
        mission=(
            "Extract high-value error patterns and trace them to code or configuration paths."
        ),
        capabilities=("log clustering", "trace analysis"),
    ),
    AgentDefinition(
        id="dependency-mapper",
        name="Dependency Mapper",
        short_name="Dependencies",
        role="specialist",
        team="investigation",
        parent_id="investigation-lead",
        mission="Map upstream and downstream health to isolate the failing boundary.",
        capabilities=("topology analysis", "dependency health"),
    ),
    AgentDefinition(
        id="response-lead",
        name="Response Orchestrator",
        short_name="Response",
        role="sub-orchestrator",
        team="response",
        parent_id=MAIN_ORCHESTRATOR_ID,
        mission="Build a reversible mitigation plan and coordinate recovery after approval.",
        capabilities=("mitigation planning", "risk control", "recovery coordination"),
    ),
    AgentDefinition(
        id="mitigation-strategist",
        name="Mitigation Strategist",
        short_name="Mitigation",
        role="specialist",
        team="response",
        parent_id="response-lead",
        mission="Rank the fastest safe options for stopping customer impact.",
        capabilities=("option analysis", "blast-radius reduction"),
    ),
    AgentDefinition(
        id="risk-reviewer",
        name="Risk & Rollback Reviewer",
        short_name="Risk",
        role="specialist",
        team="response",
        parent_id="response-lead",
        mission="Challenge the proposed mitigation and define explicit rollback triggers.",
        capabilities=("risk review", "rollback design"),
    ),
    AgentDefinition(
        id="recovery-verifier",
        name="Recovery Verifier",
        short_name="Verify",
        role="specialist",
        team="response",
        parent_id="response-lead",
        mission="Independently verify service recovery against predeclared checks.",
        capabilities=("SLO verification", "regression detection"),
    ),
    AgentDefinition(
        id="communications-lead",
        name="Communications Orchestrator",
        short_name="Comms",
        role="sub-orchestrator",
        team="communications",
        parent_id=MAIN_ORCHESTRATOR_ID,
        mission="Keep a live record and deliver accurate, audience-specific updates.",
        capabilities=("message governance", "timeline ownership", "stakeholder alignment"),
    ),
    AgentDefinition(
        id="incident-scribe",
        name="Incident Scribe",
        short_name="Scribe",
        role="specialist",
        team="communications",
        parent_id="communications-lead",
        mission="Maintain a factual, timestamped incident timeline and decision log.",
        capabilities=("timeline capture", "decision logging"),
    ),
    AgentDefinition(
        id="stakeholder-liaison",
        name="Stakeholder Liaison",
        short_name="Liaison",
        role="specialist",
        team="communications",
        parent_id="communications-lead",
        mission="Draft concise updates without leaking unverified technical claims.",
        capabilities=("status updates", "audience translation"),
    ),
    AgentDefinition(
        id="postmortem-analyst",
        name="Postmortem Analyst",
        short_name="Postmortem",
        role="specialist",
        team="communications",
        parent_id="communications-lead",
        mission="Create a blameless causal summary and concrete follow-up actions.",
        capabilities=("causal narrative", "follow-up design"),
    ),
)

AGENTS_BY_ID: dict[str, AgentDefinition] = {agent.id: agent for agent in AGENT_CATALOG}


def get_agent_definition(agent_id: str) -> AgentDefinition:
    agent = AGENTS_BY_ID.get(agent_id)
    if agent is None:
        raise KeyError(f"Unknown agent: {agent_id}")
    return agent


def get_team_orchestrator(team: OperationalTeam) -> AgentDefinition:
    return get_agent_definition(TEAM_ORCHESTRATOR_IDS[team])


def get_team_specialists(team: OperationalTeam) -> list[AgentDefinition]:
    return [agent for agent in AGENT_CATALOG if agent.team == team and agent.role == "specialist"]


def create_agent_runtime() -> list[AgentRuntime]:
    """Build the initial runtime state for every agent in the hierarchy."""
    return [
        AgentRuntime(
            id=agent.id,
            name=agent.name,
            short_name=agent.short_name,
            role=agent.role,
            team=agent.team,
            parent_id=agent.parent_id,
            mission=agent.mission,
            capabilities=list(agent.capabilities),
            status="queued",
            current_task=None,
            output_summary=None,
            started_at=None,
            completed_at=None,
        )
        for agent in AGENT_CATALOG
    ]
