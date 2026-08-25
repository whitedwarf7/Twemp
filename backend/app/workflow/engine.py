"""Deterministic orchestration for the hierarchical incident-response workflow.

Application code owns phase transitions, concurrency, event ordering, and the human approval
boundary. Providers only supply bounded reasoning.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import uuid4

from app.workflow.catalog import (
    AGENTS_BY_ID,
    MAIN_ORCHESTRATOR_ID,
    create_agent_runtime,
    get_agent_definition,
    get_team_orchestrator,
)
from app.workflow.provider import (
    AgentProvider,
    ClosureTask,
    PlanTask,
    SpecialistTask,
    TeamSynthesisTask,
    VerificationTask,
)
from app.workflow.schemas import (
    AgentRuntime,
    AgentStatus,
    ApprovalDecision,
    ApprovalRequest,
    EventLevel,
    IncidentInput,
    OperationalTeam,
    Team,
    WorkflowEvent,
    WorkflowEventType,
    WorkflowMetrics,
    WorkflowRun,
    utc_now,
)

TEAM_MISSIONS: dict[OperationalTeam, str] = {
    "triage": (
        "Correlate the incoming signals, confirm severity and impact, and identify changes near "
        "incident onset."
    ),
    "investigation": (
        "Gather independent metrics, log, and dependency evidence to rank causal hypotheses."
    ),
    "response": (
        "Design the smallest reversible mitigation, challenge its risks, and declare rollback "
        "triggers."
    ),
    "communications": (
        "Maintain a factual timeline and prepare a concise stakeholder update from confirmed "
        "evidence."
    ),
}

PLANNING_SPECIALISTS: dict[OperationalTeam, tuple[str, ...]] = {
    "triage": ("alert-correlator", "impact-analyst", "change-intelligence"),
    "investigation": ("telemetry-analyst", "log-investigator", "dependency-mapper"),
    "response": ("mitigation-strategist", "risk-reviewer"),
    "communications": ("incident-scribe", "stakeholder-liaison"),
}

_TERMINAL_STATUSES: frozenset[AgentStatus] = frozenset({"completed", "cancelled", "failed"})

_FINDING_LEVELS: dict[str, EventLevel] = {
    "critical": "critical",
    "warning": "warning",
    "info": "success",
}


class WorkflowStateError(RuntimeError):
    """Raised when a workflow transition is requested that the current state does not allow."""


def _get_runtime_agent(run: WorkflowRun, agent_id: str) -> AgentRuntime:
    for agent in run.agents:
        if agent.id == agent_id:
            return agent
    raise KeyError(f"Runtime agent not found: {agent_id}")


def _update_agent(
    run: WorkflowRun,
    agent_id: str,
    status: AgentStatus,
    current_task: str | None,
    output_summary: str | None = None,
) -> None:
    agent = _get_runtime_agent(run, agent_id)
    timestamp = utc_now()
    agent.status = status
    agent.current_task = current_task
    if status == "running" and agent.started_at is None:
        agent.started_at = timestamp
    if status in _TERMINAL_STATUSES:
        agent.completed_at = timestamp
    if output_summary:
        agent.output_summary = output_summary
    run.updated_at = timestamp


def _append_event(
    run: WorkflowRun,
    *,
    event_type: WorkflowEventType,
    actor_id: str,
    title: str,
    detail: str,
    actor_name: str | None = None,
    team: Team | None = None,
    level: EventLevel = "neutral",
) -> None:
    definition = AGENTS_BY_ID.get(actor_id)
    sequence = len(run.events) + 1
    timestamp = utc_now()
    run.events.append(
        WorkflowEvent(
            id=f"{run.id}-event-{sequence}",
            sequence=sequence,
            timestamp=timestamp,
            type=event_type,
            phase=run.phase,
            actor_id=actor_id,
            actor_name=actor_name or (definition.name if definition else "Human approver"),
            team=team or (definition.team if definition else "command"),
            title=title,
            detail=detail,
            level=level,
        )
    )
    run.updated_at = timestamp


def _refresh_metrics(run: WorkflowRun) -> None:
    confidence_sources = [finding.confidence for finding in run.findings]
    confidence_sources += [report.confidence for report in run.team_reports]
    average_confidence = (
        sum(confidence_sources) / len(confidence_sources) if confidence_sources else 0.0
    )

    run.metrics = WorkflowMetrics(
        agents_total=len(run.agents),
        agents_completed=sum(1 for agent in run.agents if agent.status == "completed"),
        active_agents=sum(1 for agent in run.agents if agent.status == "running"),
        tasks_completed=(
            len(run.findings)
            + len(run.team_reports)
            + int(run.plan is not None)
            + int(run.verification is not None)
            + int(run.outcome is not None)
        ),
        handoffs=sum(1 for event in run.events if event.type == "delegation"),
        confidence=round(average_confidence, 2),
    )


def _create_run(incident: IncidentInput, provider: AgentProvider) -> WorkflowRun:
    timestamp: datetime = utc_now()
    return WorkflowRun(
        id=f"INC-{uuid4().hex[:8].upper()}",
        incident=incident,
        mode=provider.mode,
        status="running",
        phase="intake",
        started_at=timestamp,
        updated_at=timestamp,
        agents=create_agent_runtime(),
        events=[],
        findings=[],
        team_reports=[],
        plan=None,
        approval=None,
        verification=None,
        outcome=None,
        metrics=WorkflowMetrics(
            agents_total=0,
            agents_completed=0,
            active_agents=0,
            tasks_completed=0,
            handoffs=0,
            confidence=0,
        ),
    )


async def _run_team(run: WorkflowRun, provider: AgentProvider, team: OperationalTeam) -> None:
    """Delegate to a sub-orchestrator, fan out its specialists, and record one team report."""
    orchestrator = get_team_orchestrator(team)
    specialists = [get_agent_definition(agent_id) for agent_id in PLANNING_SPECIALISTS[team]]
    objective = TEAM_MISSIONS[team]
    prior_findings = tuple(run.findings)
    prior_reports = tuple(run.team_reports)

    _update_agent(run, orchestrator.id, "running", objective)
    _append_event(
        run,
        event_type="delegation",
        actor_id=MAIN_ORCHESTRATOR_ID,
        title=f"Command delegated to {orchestrator.short_name}",
        detail=objective,
    )

    for specialist in specialists:
        _update_agent(run, specialist.id, "running", specialist.mission)
        _append_event(
            run,
            event_type="delegation",
            actor_id=orchestrator.id,
            title=f"{orchestrator.short_name} \u2192 {specialist.short_name}",
            detail=specialist.mission,
        )
        _append_event(
            run,
            event_type="agent-started",
            actor_id=specialist.id,
            title=f"{specialist.short_name} started analysis",
            detail=specialist.mission,
        )

    team_findings = await asyncio.gather(
        *(
            provider.run_specialist(
                SpecialistTask(
                    run_id=run.id,
                    agent=specialist,
                    incident=run.incident,
                    objective=objective,
                    prior_findings=prior_findings,
                    team_reports=prior_reports,
                    plan=run.plan,
                )
            )
            for specialist in specialists
        )
    )

    for finding in team_findings:
        run.findings.append(finding)
        _update_agent(run, finding.agent_id, "completed", None, finding.headline)
        _append_event(
            run,
            event_type="finding",
            actor_id=finding.agent_id,
            title=finding.headline,
            detail=finding.detail,
            level=_FINDING_LEVELS[finding.severity],
        )

    report = await provider.synthesize_team(
        TeamSynthesisTask(
            run_id=run.id,
            orchestrator=orchestrator,
            incident=run.incident,
            findings=tuple(team_findings),
            prior_reports=prior_reports,
        )
    )
    run.team_reports.append(report)
    _update_agent(run, orchestrator.id, "completed", None, report.title)
    _append_event(
        run,
        event_type="communication" if team == "communications" else "synthesis",
        actor_id=orchestrator.id,
        title=report.title,
        detail=report.recommendation,
        level="success",
    )
    _refresh_metrics(run)


def _fail_run(run: WorkflowRun, detail: str) -> WorkflowRun:
    run.status = "failed"
    run.phase = "failed"
    for agent in [agent for agent in run.agents if agent.status == "running"]:
        _update_agent(run, agent.id, "failed", None, "Execution stopped safely")
    _append_event(
        run,
        event_type="workflow-failed",
        actor_id=MAIN_ORCHESTRATOR_ID,
        title="Workflow stopped safely",
        detail=detail,
        level="critical",
    )
    _refresh_metrics(run)
    return run


async def start_workflow(incident: IncidentInput, provider: AgentProvider) -> WorkflowRun:
    """Run every pre-approval phase and stop at the human decision boundary."""
    run = _create_run(incident, provider)

    try:
        _update_agent(
            run,
            MAIN_ORCHESTRATOR_ID,
            "running",
            "Establishing command and assigning response teams",
        )
        _append_event(
            run,
            event_type="workflow-started",
            actor_id=MAIN_ORCHESTRATOR_ID,
            title=f"{incident.severity} command activated",
            detail=(
                f"Incident command opened for {incident.service} in {incident.region}. Four "
                "workstreams will report through one command node."
            ),
            level="critical",
        )

        run.phase = "triage"
        await _run_team(run, provider, "triage")

        run.phase = "investigation"
        await _run_team(run, provider, "investigation")

        run.phase = "planning"
        await _run_team(run, provider, "response")
        _update_agent(
            run,
            "response-lead",
            "running",
            "Converting evidence into an approval-gated remediation plan",
        )
        plan = await provider.draft_plan(
            PlanTask(
                run_id=run.id,
                orchestrator=get_team_orchestrator("response"),
                incident=run.incident,
                findings=tuple(run.findings),
                reports=tuple(run.team_reports),
            )
        )
        run.plan = plan
        _update_agent(run, "response-lead", "completed", None, plan.summary)
        _append_event(
            run,
            event_type="plan-ready",
            actor_id="response-lead",
            title="Bounded remediation plan ready",
            detail=(
                f"{len(plan.actions)} reversible steps prepared with {plan.risk_level} aggregate "
                "risk. No action has been executed."
            ),
            level="warning",
        )

        await _run_team(run, provider, "communications")

        run.phase = "approval"
        run.status = "awaiting_approval"
        run.approval = ApprovalRequest(
            id=f"{run.id}-approval-1",
            status="pending",
            requested_at=utc_now(),
            decided_at=None,
            decided_by=None,
            note=None,
            plan=plan,
        )
        _update_agent(run, "recovery-verifier", "blocked", "Waiting for approved remediation")
        _update_agent(run, "postmortem-analyst", "blocked", "Waiting for incident outcome")
        _update_agent(
            run,
            MAIN_ORCHESTRATOR_ID,
            "blocked",
            "Human approval required before remediation",
            "Evidence synthesized; approval required",
        )
        _append_event(
            run,
            event_type="approval-requested",
            actor_id=MAIN_ORCHESTRATOR_ID,
            title="Human approval required",
            detail=(
                "The workflow is paused at the remediation boundary. Review blast radius, "
                "rollback criteria, and validation checks before deciding."
            ),
            level="warning",
        )
        _refresh_metrics(run)
        return run
    except Exception:
        return _fail_run(
            run,
            "An agent provider or validation boundary failed before approval. No remediation was "
            "attempted.",
        )


async def decide_workflow(
    current_run: WorkflowRun,
    decision: ApprovalDecision,
    provider: AgentProvider,
) -> WorkflowRun:
    """Apply the single human decision and, when approved, resume the post-approval phases."""
    run = current_run.model_copy(deep=True)

    if (
        run.status != "awaiting_approval"
        or run.approval is None
        or run.approval.status != "pending"
    ):
        raise WorkflowStateError("This workflow is not waiting for an approval decision")
    if run.plan is None:
        raise WorkflowStateError("The workflow has no remediation plan to approve")

    run.approval.decided_at = utc_now()
    run.approval.decided_by = decision.reviewer
    run.approval.note = decision.note or None

    if decision.decision == "reject":
        run.approval.status = "rejected"
        run.status = "rejected"
        run.phase = "rejected"
        _update_agent(
            run,
            MAIN_ORCHESTRATOR_ID,
            "completed",
            None,
            "Remediation rejected; no changes executed",
        )
        for agent_id in ("recovery-verifier", "postmortem-analyst"):
            _update_agent(run, agent_id, "cancelled", None, "Cancelled after plan rejection")
        _append_event(
            run,
            event_type="approval-rejected",
            actor_id="human-approver",
            actor_name=decision.reviewer,
            team="command",
            title="Remediation plan rejected",
            detail=(
                decision.note or "The reviewer rejected the plan. No remediation was executed."
            ),
            level="critical",
        )
        _append_event(
            run,
            event_type="communication",
            actor_id="stakeholder-liaison",
            title="Decision recorded for stakeholders",
            detail=(
                "The proposed mitigation was not approved. Incident state and evidence are "
                "retained for the next command decision."
            ),
            level="warning",
        )
        _refresh_metrics(run)
        return run

    run.approval.status = "approved"
    run.status = "running"
    run.phase = "remediation"
    _update_agent(run, MAIN_ORCHESTRATOR_ID, "running", "Supervising approved remediation")
    _update_agent(
        run,
        "response-lead",
        "running",
        "Coordinating approved remediation simulation",
    )
    _append_event(
        run,
        event_type="approval-granted",
        actor_id="human-approver",
        actor_name=decision.reviewer,
        team="command",
        title="Remediation plan approved",
        detail=(decision.note or "The reviewer approved the bounded plan for simulated execution."),
        level="success",
    )

    try:
        for action in run.plan.actions:
            _append_event(
                run,
                event_type="remediation",
                actor_id=action.owner_agent_id,
                title=action.title,
                detail=(
                    f"Controlled simulation: {action.detail} Expected signal: "
                    f"{action.expected_signal}."
                ),
                level="critical" if action.risk == "high" else "warning",
            )
        _update_agent(
            run,
            "response-lead",
            "completed",
            None,
            "Approved remediation simulation completed",
        )

        run.phase = "verification"
        _update_agent(
            run,
            "recovery-verifier",
            "running",
            "Checking recovery against predeclared success criteria",
        )
        _append_event(
            run,
            event_type="agent-started",
            actor_id="recovery-verifier",
            title="Independent recovery verification started",
            detail=(
                "All declared validation checks must pass before command can resolve the incident."
            ),
        )
        verification = await provider.verify_recovery(
            VerificationTask(
                run_id=run.id,
                agent=get_agent_definition("recovery-verifier"),
                incident=run.incident,
                plan=run.plan,
                findings=tuple(run.findings),
            )
        )
        run.verification = verification
        _update_agent(
            run,
            "recovery-verifier",
            "completed" if verification.status == "passed" else "failed",
            None,
            verification.summary,
        )
        _append_event(
            run,
            event_type="verification",
            actor_id="recovery-verifier",
            title=(
                "Recovery checks passed"
                if verification.status == "passed"
                else "Recovery checks failed"
            ),
            detail=verification.summary,
            level="success" if verification.status == "passed" else "critical",
        )

        if verification.status == "failed":
            _update_agent(
                run,
                "postmortem-analyst",
                "cancelled",
                None,
                "Resolution blocked by failed verification",
            )
            return _fail_run(
                run,
                "Recovery verification failed. Command remains fail-closed and requires a new "
                "plan.",
            )

        _update_agent(run, "communications-lead", "running", "Preparing resolution communication")
        _update_agent(
            run,
            "postmortem-analyst",
            "running",
            "Drafting the blameless incident outcome",
        )
        outcome = await provider.close_incident(
            ClosureTask(
                run_id=run.id,
                agent=get_agent_definition("postmortem-analyst"),
                incident=run.incident,
                plan=run.plan,
                verification=verification,
                findings=tuple(run.findings),
                reports=tuple(run.team_reports),
            )
        )
        run.outcome = outcome
        _update_agent(run, "postmortem-analyst", "completed", None, outcome.root_cause)
        _update_agent(
            run,
            "communications-lead",
            "completed",
            None,
            "Recovery update and postmortem seed prepared",
        )
        _append_event(
            run,
            event_type="communication",
            actor_id="postmortem-analyst",
            title="Blameless incident outcome prepared",
            detail=outcome.root_cause,
            level="success",
        )

        run.status = "completed"
        run.phase = "resolved"
        _update_agent(
            run,
            MAIN_ORCHESTRATOR_ID,
            "completed",
            None,
            "Incident resolved and follow-up work captured",
        )
        _append_event(
            run,
            event_type="workflow-completed",
            actor_id=MAIN_ORCHESTRATOR_ID,
            title="Incident resolved",
            detail=(
                "Verification passed, the recovery update is ready, and prevention work has been "
                "added to the incident outcome."
            ),
            level="success",
        )
        _refresh_metrics(run)
        return run
    except Exception:
        return _fail_run(
            run,
            "A provider or validation boundary failed after approval. Execution stopped without "
            "attempting any unplanned action.",
        )
