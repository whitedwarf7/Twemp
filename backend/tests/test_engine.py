"""Orchestration guarantees: hierarchy, ordering, the approval gate, and fail-closed behavior."""

from __future__ import annotations

from collections import Counter

import pytest

from app.workflow.catalog import AGENT_CATALOG, AGENTS_BY_ID, MAIN_ORCHESTRATOR_ID
from app.workflow.demo_provider import DemoAgentProvider
from app.workflow.engine import WorkflowStateError, decide_workflow, start_workflow
from app.workflow.provider import AgentProvider, ClosureTask, SpecialistTask, VerificationTask
from app.workflow.schemas import (
    DEFAULT_INCIDENT,
    AgentFinding,
    ApprovalDecision,
    IncidentOutcome,
    VerificationCheck,
    VerificationReport,
    WorkflowRun,
)

APPROVE = ApprovalDecision(decision="approve", reviewer="Primary on-call", note="Reviewed")


class FailingSpecialistProvider(DemoAgentProvider):
    """Simulates a provider outage while evidence is still being gathered."""

    async def run_specialist(self, task: SpecialistTask) -> AgentFinding:
        raise RuntimeError("provider unavailable")


class FailingVerifierProvider(DemoAgentProvider):
    async def verify_recovery(self, task: VerificationTask) -> VerificationReport:
        raise RuntimeError("verification backend unavailable")


class FailedVerificationProvider(DemoAgentProvider):
    async def verify_recovery(self, task: VerificationTask) -> VerificationReport:
        return VerificationReport(
            status="failed",
            summary="Latency remained above the declared threshold after mitigation.",
            checks=[
                VerificationCheck(
                    label="Checkout p95 latency",
                    value="3.9 s",
                    status="failed",
                    detail="Still far above the 800 ms threshold",
                )
            ],
        )


class FailingClosureProvider(DemoAgentProvider):
    async def close_incident(self, task: ClosureTask) -> IncidentOutcome:
        raise RuntimeError("postmortem service unavailable")


def event_types(run: WorkflowRun) -> Counter[str]:
    return Counter(event.type for event in run.events)


def statuses(run: WorkflowRun) -> Counter[str]:
    return Counter(agent.status for agent in run.agents)


class TestPreApprovalPhases:
    async def test_the_run_stops_at_the_approval_gate(self, pending_run: WorkflowRun) -> None:
        assert pending_run.status == "awaiting_approval"
        assert pending_run.phase == "approval"
        assert pending_run.approval is not None
        assert pending_run.approval.status == "pending"
        assert pending_run.approval.decided_at is None
        assert pending_run.approval.decided_by is None
        assert pending_run.plan is not None
        assert pending_run.verification is None
        assert pending_run.outcome is None

    async def test_no_remediation_happens_before_approval(self, pending_run: WorkflowRun) -> None:
        assert event_types(pending_run)["remediation"] == 0

    async def test_every_team_contributes_findings_and_one_report(
        self, pending_run: WorkflowRun
    ) -> None:
        findings_by_team = Counter(finding.team for finding in pending_run.findings)
        reports_by_team = Counter(report.team for report in pending_run.team_reports)

        assert findings_by_team == {
            "triage": 3,
            "investigation": 3,
            "response": 2,
            "communications": 2,
        }
        assert reports_by_team == {
            "triage": 1,
            "investigation": 1,
            "response": 1,
            "communications": 1,
        }

    async def test_teams_execute_in_command_order(self, pending_run: WorkflowRun) -> None:
        report_order = [report.team for report in pending_run.team_reports]
        assert report_order == ["triage", "investigation", "response", "communications"]

    async def test_the_event_ledger_is_contiguous_and_ordered(
        self, pending_run: WorkflowRun
    ) -> None:
        sequences = [event.sequence for event in pending_run.events]
        timestamps = [event.timestamp for event in pending_run.events]

        assert sequences == list(range(1, len(pending_run.events) + 1))
        assert timestamps == sorted(timestamps)
        assert len({event.id for event in pending_run.events}) == len(pending_run.events)

    async def test_the_expected_events_are_recorded(self, pending_run: WorkflowRun) -> None:
        assert event_types(pending_run) == {
            "workflow-started": 1,
            "delegation": 14,
            "agent-started": 10,
            "finding": 10,
            "synthesis": 3,
            "communication": 1,
            "plan-ready": 1,
            "approval-requested": 1,
        }

    async def test_every_event_actor_is_a_known_agent(self, pending_run: WorkflowRun) -> None:
        for event in pending_run.events:
            assert event.actor_id in AGENTS_BY_ID
            assert event.actor_name == AGENTS_BY_ID[event.actor_id].name

    async def test_downstream_agents_are_gated_until_approval(
        self, pending_run: WorkflowRun
    ) -> None:
        by_id = {agent.id: agent for agent in pending_run.agents}

        assert by_id[MAIN_ORCHESTRATOR_ID].status == "blocked"
        assert by_id["recovery-verifier"].status == "blocked"
        assert by_id["postmortem-analyst"].status == "blocked"
        assert statuses(pending_run) == {"completed": 14, "blocked": 3}

    async def test_completed_agents_carry_timing_and_a_summary(
        self, pending_run: WorkflowRun
    ) -> None:
        completed = [agent for agent in pending_run.agents if agent.status == "completed"]

        assert len(completed) == 14
        for agent in completed:
            assert agent.started_at is not None
            assert agent.completed_at is not None
            assert agent.completed_at >= agent.started_at
            assert agent.current_task is None
            assert agent.output_summary

    async def test_metrics_summarize_the_run(self, pending_run: WorkflowRun) -> None:
        metrics = pending_run.metrics
        confidences = [finding.confidence for finding in pending_run.findings]

        assert metrics.agents_total == len(AGENT_CATALOG)
        assert metrics.agents_completed == 14
        assert metrics.active_agents == 0
        assert metrics.handoffs == event_types(pending_run)["delegation"]
        assert metrics.tasks_completed == 15
        assert min(confidences) <= metrics.confidence <= max(confidences)

    async def test_the_pending_approval_carries_the_drafted_plan(
        self, pending_run: WorkflowRun
    ) -> None:
        assert pending_run.approval is not None
        assert pending_run.approval.plan == pending_run.plan

    async def test_run_identity_and_mode_are_recorded(self, provider: AgentProvider) -> None:
        first = await start_workflow(DEFAULT_INCIDENT, provider)
        second = await start_workflow(DEFAULT_INCIDENT, provider)

        assert first.id != second.id
        assert first.id.startswith("INC-")
        assert first.mode == provider.mode
        assert first.incident == DEFAULT_INCIDENT


class TestApproval:
    async def test_approval_resumes_the_remaining_phases(self, completed_run: WorkflowRun) -> None:
        assert completed_run.status == "completed"
        assert completed_run.phase == "resolved"
        assert completed_run.approval is not None
        assert completed_run.approval.status == "approved"
        assert completed_run.approval.decided_by == "Primary on-call"
        assert completed_run.approval.decided_at is not None
        assert completed_run.verification is not None
        assert completed_run.verification.status == "passed"
        assert completed_run.outcome is not None

    async def test_remediation_only_follows_the_approval_event(
        self, completed_run: WorkflowRun
    ) -> None:
        order = [event.type for event in completed_run.events]
        first_remediation = order.index("remediation")

        assert order.index("approval-granted") < first_remediation
        assert order.index("verification") > first_remediation
        assert order.index("workflow-completed") > order.index("verification")

    async def test_each_planned_action_is_executed_once_as_a_simulation(
        self, completed_run: WorkflowRun
    ) -> None:
        assert completed_run.plan is not None
        remediation = [event for event in completed_run.events if event.type == "remediation"]

        assert len(remediation) == len(completed_run.plan.actions)
        assert [event.title for event in remediation] == [
            action.title for action in completed_run.plan.actions
        ]
        assert all(event.detail.startswith("Controlled simulation:") for event in remediation)

    async def test_the_whole_hierarchy_settles(self, completed_run: WorkflowRun) -> None:
        assert statuses(completed_run) == {"completed": 17}
        assert completed_run.metrics.active_agents == 0
        assert completed_run.metrics.agents_completed == 17
        assert completed_run.metrics.tasks_completed == 17

    async def test_the_post_approval_ledger_is_recorded(self, completed_run: WorkflowRun) -> None:
        assert event_types(completed_run) == {
            "workflow-started": 1,
            "delegation": 14,
            "agent-started": 11,
            "finding": 10,
            "synthesis": 3,
            "communication": 2,
            "plan-ready": 1,
            "approval-requested": 1,
            "approval-granted": 1,
            "remediation": 3,
            "verification": 1,
            "workflow-completed": 1,
        }
        sequences = [event.sequence for event in completed_run.events]
        assert sequences == list(range(1, len(completed_run.events) + 1))

    async def test_an_empty_note_falls_back_to_a_default_message(
        self, pending_run: WorkflowRun, provider: AgentProvider
    ) -> None:
        run = await decide_workflow(
            pending_run, ApprovalDecision(decision="approve", reviewer="On-call"), provider
        )

        granted = next(event for event in run.events if event.type == "approval-granted")
        assert run.approval is not None
        assert run.approval.note is None
        assert granted.detail == "The reviewer approved the bounded plan for simulated execution."


class TestRejection:
    async def test_rejection_stops_the_workflow(self, rejected_run: WorkflowRun) -> None:
        assert rejected_run.status == "rejected"
        assert rejected_run.phase == "rejected"
        assert rejected_run.approval is not None
        assert rejected_run.approval.status == "rejected"
        assert rejected_run.approval.decided_by == "Incident commander"
        assert rejected_run.verification is None
        assert rejected_run.outcome is None

    async def test_rejection_never_executes_remediation(self, rejected_run: WorkflowRun) -> None:
        assert event_types(rejected_run)["remediation"] == 0
        assert event_types(rejected_run)["approval-rejected"] == 1

    async def test_downstream_agents_are_cancelled(self, rejected_run: WorkflowRun) -> None:
        by_id = {agent.id: agent for agent in rejected_run.agents}

        assert by_id["recovery-verifier"].status == "cancelled"
        assert by_id["postmortem-analyst"].status == "cancelled"
        assert by_id[MAIN_ORCHESTRATOR_ID].status == "completed"
        assert statuses(rejected_run) == {"completed": 15, "cancelled": 2}

    async def test_the_reviewer_note_is_published_to_stakeholders(
        self, rejected_run: WorkflowRun
    ) -> None:
        rejection = next(
            event for event in rejected_run.events if event.type == "approval-rejected"
        )

        assert rejection.detail == "Too broad"
        assert rejection.actor_name == "Incident commander"
        assert rejected_run.events[-1].type == "communication"


class TestDecisionGuards:
    async def test_a_settled_approval_cannot_be_decided_again(
        self, completed_run: WorkflowRun, provider: AgentProvider
    ) -> None:
        with pytest.raises(WorkflowStateError, match="not waiting for an approval decision"):
            await decide_workflow(completed_run, APPROVE, provider)

    async def test_a_rejected_run_cannot_be_approved_later(
        self, rejected_run: WorkflowRun, provider: AgentProvider
    ) -> None:
        with pytest.raises(WorkflowStateError, match="not waiting for an approval decision"):
            await decide_workflow(rejected_run, APPROVE, provider)

    async def test_a_pending_approval_without_a_plan_is_refused(
        self, pending_run: WorkflowRun, provider: AgentProvider
    ) -> None:
        without_plan = pending_run.model_copy(deep=True, update={"plan": None})

        with pytest.raises(WorkflowStateError, match="no remediation plan"):
            await decide_workflow(without_plan, APPROVE, provider)

    async def test_deciding_does_not_mutate_the_caller_state(
        self, pending_run: WorkflowRun, provider: AgentProvider
    ) -> None:
        event_count = len(pending_run.events)

        await decide_workflow(pending_run, APPROVE, provider)

        assert pending_run.status == "awaiting_approval"
        assert pending_run.approval is not None
        assert pending_run.approval.status == "pending"
        assert len(pending_run.events) == event_count


class TestFailClosedBehavior:
    async def test_a_provider_outage_before_approval_stops_the_run(self) -> None:
        run = await start_workflow(DEFAULT_INCIDENT, FailingSpecialistProvider())

        assert run.status == "failed"
        assert run.phase == "failed"
        assert run.plan is None
        assert run.approval is None
        assert event_types(run)["workflow-failed"] == 1
        assert event_types(run)["remediation"] == 0
        assert run.events[-1].level == "critical"
        assert statuses(run)["running"] == 0
        assert statuses(run)["failed"] >= 1

    async def test_a_verification_outage_after_approval_stops_the_run(
        self, pending_run: WorkflowRun
    ) -> None:
        run = await decide_workflow(pending_run, APPROVE, FailingVerifierProvider())

        assert run.status == "failed"
        assert run.phase == "failed"
        assert run.verification is None
        assert run.outcome is None
        assert event_types(run)["workflow-completed"] == 0
        assert event_types(run)["workflow-failed"] == 1

    async def test_failed_verification_blocks_resolution(self, pending_run: WorkflowRun) -> None:
        run = await decide_workflow(pending_run, APPROVE, FailedVerificationProvider())

        by_id = {agent.id: agent for agent in run.agents}
        assert run.status == "failed"
        assert run.verification is not None
        assert run.verification.status == "failed"
        assert run.outcome is None
        assert by_id["recovery-verifier"].status == "failed"
        assert by_id["postmortem-analyst"].status == "cancelled"
        assert event_types(run)["workflow-completed"] == 0

    async def test_a_closure_outage_stops_the_run_after_successful_verification(
        self, pending_run: WorkflowRun
    ) -> None:
        run = await decide_workflow(pending_run, APPROVE, FailingClosureProvider())

        assert run.status == "failed"
        assert run.verification is not None
        assert run.verification.status == "passed"
        assert run.outcome is None
        assert event_types(run)["workflow-completed"] == 0
