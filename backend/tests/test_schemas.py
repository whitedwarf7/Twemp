"""Contract validation: every constraint, alias, and serialization rule.

Each test pins a boundary that the frontend and API consumers depend on.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from app.workflow.schemas import (
    DEFAULT_INCIDENT,
    AgentFinding,
    AgentRuntime,
    ApprovalDecision,
    IncidentInput,
    RemediationAction,
    RemediationPlan,
    TeamReport,
    VerificationCheck,
    VerificationReport,
    WorkflowEvent,
    WorkflowMetrics,
    utc_now,
)


def incident(**overrides: Any) -> dict[str, Any]:
    return {**DEFAULT_INCIDENT.model_dump(mode="json", by_alias=True), **overrides}


def event(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "INC-1-event-1",
        "sequence": 1,
        "timestamp": "2026-08-25T06:58:35.536Z",
        "type": "finding",
        "phase": "triage",
        "actorId": "alert-correlator",
        "actorName": "Alert Correlator",
        "team": "triage",
        "title": "Alerts share one onset window",
        "detail": "Latency and error alerts moved together.",
        "level": "warning",
    }
    return {**base, **overrides}


def finding(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "INC-1-finding-alert-correlator",
        "agentId": "alert-correlator",
        "team": "triage",
        "headline": "Alerts share one onset window",
        "detail": "Latency and error alerts moved together within two minutes.",
        "evidence": ["First breach at 14:32 UTC"],
        "confidence": 0.9,
        "severity": "critical",
    }
    return {**base, **overrides}


def action(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "action-1",
        "title": "Canary rollback",
        "detail": "Roll back five percent of regional instances first.",
        "ownerAgentId": "response-lead",
        "risk": "medium",
        "reversible": True,
        "expectedSignal": "p95 latency below 800 ms",
    }
    return {**base, **overrides}


def plan(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "INC-1-plan-1",
        "hypothesis": "A timeout branch leaks gateway connections.",
        "summary": "Canary a rollback and then drain the retry queue.",
        "riskLevel": "medium",
        "blastRadius": "One region only",
        "actions": [action()],
        "rollback": "Restore the previous release if error rate exceeds two percent.",
        "validationChecks": ["p95 latency below 800 ms"],
    }
    return {**base, **overrides}


class TestIncidentInput:
    def test_default_incident_round_trips_through_camel_case_json(self) -> None:
        payload = DEFAULT_INCIDENT.model_dump(mode="json", by_alias=True)
        assert IncidentInput.model_validate(payload) == DEFAULT_INCIDENT

    @pytest.mark.parametrize("length", [5, 120])
    def test_title_accepts_boundary_lengths(self, length: int) -> None:
        assert len(IncidentInput.model_validate(incident(title="t" * length)).title) == length

    @pytest.mark.parametrize("length", [4, 121])
    def test_title_rejects_out_of_range_lengths(self, length: int) -> None:
        with pytest.raises(ValidationError):
            IncidentInput.model_validate(incident(title="t" * length))

    @pytest.mark.parametrize("length", [20, 2000])
    def test_description_accepts_boundary_lengths(self, length: int) -> None:
        parsed = IncidentInput.model_validate(incident(description="d" * length))
        assert len(parsed.description) == length

    @pytest.mark.parametrize("length", [19, 2001])
    def test_description_rejects_out_of_range_lengths(self, length: int) -> None:
        with pytest.raises(ValidationError):
            IncidentInput.model_validate(incident(description="d" * length))

    @pytest.mark.parametrize("service", ["a-b", "svc.name", "svc_name", "team/svc", "AB", "a" * 80])
    def test_service_accepts_safe_identifiers(self, service: str) -> None:
        assert IncidentInput.model_validate(incident(service=service)).service == service

    @pytest.mark.parametrize(
        "service",
        ["has space", "semi;colon", "quote'", "a", "a" * 81, "unicode\u00e9", "star*"],
    )
    def test_service_rejects_unsafe_identifiers(self, service: str) -> None:
        with pytest.raises(ValidationError):
            IncidentInput.model_validate(incident(service=service))

    @pytest.mark.parametrize("region", ["eu", "a" * 80])
    def test_region_accepts_boundary_lengths(self, region: str) -> None:
        assert IncidentInput.model_validate(incident(region=region)).region == region

    @pytest.mark.parametrize("region", ["e", "a" * 81])
    def test_region_rejects_out_of_range_lengths(self, region: str) -> None:
        with pytest.raises(ValidationError):
            IncidentInput.model_validate(incident(region=region))

    def test_signals_accept_the_maximum_supported_count(self) -> None:
        parsed = IncidentInput.model_validate(incident(signals=[f"signal {i}" for i in range(12)]))
        assert len(parsed.signals) == 12

    @pytest.mark.parametrize(
        "signals",
        [[], [f"signal {i}" for i in range(13)], ["ab"], ["s" * 241]],
        ids=["empty", "too-many", "item-too-short", "item-too-long"],
    )
    def test_signals_reject_invalid_collections(self, signals: list[str]) -> None:
        with pytest.raises(ValidationError):
            IncidentInput.model_validate(incident(signals=signals))

    def test_surrounding_whitespace_is_stripped(self) -> None:
        parsed = IncidentInput.model_validate(
            incident(
                title="  Checkout latency surge  ",
                service="  payment-router  ",
                region="  eu-central  ",
                signals=["  p95 latency 8.4 s  "],
            )
        )
        assert parsed.title == "Checkout latency surge"
        assert parsed.service == "payment-router"
        assert parsed.region == "eu-central"
        assert parsed.signals == ["p95 latency 8.4 s"]

    def test_whitespace_only_values_fail_the_minimum_length(self) -> None:
        with pytest.raises(ValidationError):
            IncidentInput.model_validate(incident(title="        "))

    def test_severity_is_restricted_to_the_supported_levels(self) -> None:
        with pytest.raises(ValidationError):
            IncidentInput.model_validate(incident(severity="SEV-9"))

    def test_unknown_fields_are_rejected(self) -> None:
        with pytest.raises(ValidationError) as error:
            IncidentInput.model_validate(incident(runbook="delete-database"))
        assert "runbook" in str(error.value)

    def test_missing_required_fields_are_reported(self) -> None:
        payload = incident()
        del payload["service"]
        with pytest.raises(ValidationError) as error:
            IncidentInput.model_validate(payload)
        assert "service" in str(error.value)


class TestAliasesAndSerialization:
    def test_json_uses_camel_case_keys(self) -> None:
        runtime = AgentRuntime(
            id="triage-lead",
            name="Triage Orchestrator",
            short_name="Triage",
            role="sub-orchestrator",
            team="triage",
            parent_id="incident-commander",
            mission="Establish severity and scope.",
            capabilities=["scope control"],
            status="queued",
            current_task=None,
            output_summary=None,
            started_at=None,
            completed_at=None,
        )
        payload = runtime.model_dump(mode="json", by_alias=True)
        assert payload["shortName"] == "Triage"
        assert payload["parentId"] == "incident-commander"
        assert payload["currentTask"] is None
        assert payload["startedAt"] is None
        assert "short_name" not in payload
        assert "parent_id" not in payload

    def test_models_accept_both_field_names_and_aliases(self) -> None:
        camel_case = AgentFinding.model_validate(finding())

        snake_case_payload = {
            "id": "INC-1-finding-alert-correlator",
            "agent_id": "alert-correlator",
            "team": "triage",
            "headline": "Alerts share one onset window",
            "detail": "Latency and error alerts moved together within two minutes.",
            "evidence": ["First breach at 14:32 UTC"],
            "confidence": 0.9,
            "severity": "critical",
        }
        snake_case = AgentFinding.model_validate(snake_case_payload)

        assert camel_case == snake_case
        assert snake_case.agent_id == "alert-correlator"

    def test_timestamps_serialize_as_iso_8601_with_millisecond_z_suffix(self) -> None:
        parsed = WorkflowEvent.model_validate(event(timestamp="2026-08-25T06:58:35.536000Z"))
        assert parsed.model_dump(mode="json")["timestamp"] == "2026-08-25T06:58:35.536Z"

    def test_non_utc_offsets_are_normalized_to_utc(self) -> None:
        aware = datetime(2026, 8, 25, 8, 58, 35, 536000, tzinfo=timezone(timedelta(hours=2)))
        parsed = WorkflowEvent.model_validate(event(timestamp=aware))
        assert parsed.model_dump(mode="json")["timestamp"] == "2026-08-25T06:58:35.536Z"

    def test_naive_timestamps_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowEvent.model_validate(event(timestamp=datetime(2026, 8, 25, 6, 58, 35)))

    def test_utc_now_returns_an_aware_utc_value(self) -> None:
        value = utc_now()
        assert value.tzinfo is not None
        assert value.utcoffset() == timedelta(0)

    def test_assignment_is_validated_after_construction(self) -> None:
        parsed = AgentFinding.model_validate(finding())
        with pytest.raises(ValidationError):
            parsed.confidence = 1.5


class TestNumericAndCollectionBounds:
    @pytest.mark.parametrize("confidence", [0.0, 1.0])
    def test_confidence_accepts_the_unit_interval(self, confidence: float) -> None:
        assert AgentFinding.model_validate(finding(confidence=confidence)).confidence == confidence

    @pytest.mark.parametrize("confidence", [-0.01, 1.01])
    def test_confidence_rejects_values_outside_the_unit_interval(self, confidence: float) -> None:
        with pytest.raises(ValidationError):
            AgentFinding.model_validate(finding(confidence=confidence))

    def test_finding_evidence_must_be_present_and_bounded(self) -> None:
        assert len(AgentFinding.model_validate(finding(evidence=["e" * 320] * 8)).evidence) == 8
        with pytest.raises(ValidationError):
            AgentFinding.model_validate(finding(evidence=[]))
        with pytest.raises(ValidationError):
            AgentFinding.model_validate(finding(evidence=["ok evidence"] * 9))

    def test_event_sequence_must_be_positive(self) -> None:
        assert WorkflowEvent.model_validate(event(sequence=1)).sequence == 1
        with pytest.raises(ValidationError):
            WorkflowEvent.model_validate(event(sequence=0))

    def test_metrics_reject_negative_counters(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowMetrics(
                agents_total=17,
                agents_completed=-1,
                active_agents=0,
                tasks_completed=0,
                handoffs=0,
                confidence=0.5,
            )

    def test_plan_requires_between_one_and_eight_actions(self) -> None:
        assert len(RemediationPlan.model_validate(plan(actions=[action()] * 8)).actions) == 8
        with pytest.raises(ValidationError):
            RemediationPlan.model_validate(plan(actions=[]))
        with pytest.raises(ValidationError):
            RemediationPlan.model_validate(plan(actions=[action()] * 9))

    def test_plan_requires_between_one_and_ten_validation_checks(self) -> None:
        parsed = RemediationPlan.model_validate(plan(validationChecks=["c" * 320] * 10))
        assert len(parsed.validation_checks) == 10
        with pytest.raises(ValidationError):
            RemediationPlan.model_validate(plan(validationChecks=[]))
        with pytest.raises(ValidationError):
            RemediationPlan.model_validate(plan(validationChecks=["check value"] * 11))

    def test_team_report_key_findings_are_bounded(self) -> None:
        report = {
            "id": "INC-1-report-triage",
            "orchestratorId": "triage-lead",
            "team": "triage",
            "title": "Scope confirmed",
            "summary": "Impact is limited to one region.",
            "keyFindings": ["One onset window"],
            "recommendation": "Prioritize the regional release path.",
            "confidence": 0.9,
        }
        assert TeamReport.model_validate(report).key_findings == ["One onset window"]
        with pytest.raises(ValidationError):
            TeamReport.model_validate({**report, "keyFindings": []})

    def test_verification_requires_at_least_one_check(self) -> None:
        check = VerificationCheck(
            label="Checkout p95 latency",
            value="612 ms",
            status="passed",
            detail="Below threshold",
        )
        report = VerificationReport(status="passed", summary="All good now.", checks=[check])
        assert len(report.checks) == 1
        with pytest.raises(ValidationError):
            VerificationReport(status="passed", summary="All good now.", checks=[])

    def test_risk_levels_are_restricted(self) -> None:
        with pytest.raises(ValidationError):
            RemediationAction.model_validate(action(risk="catastrophic"))


class TestApprovalDecision:
    def test_note_defaults_to_an_empty_string(self) -> None:
        decision = ApprovalDecision(decision="approve", reviewer="On-call")
        assert decision.note == ""

    def test_reviewer_and_note_are_stripped(self) -> None:
        decision = ApprovalDecision(decision="reject", reviewer="  On-call  ", note="  Too broad  ")
        assert decision.reviewer == "On-call"
        assert decision.note == "Too broad"

    @pytest.mark.parametrize("reviewer", ["a", "  a  ", "r" * 81])
    def test_reviewer_length_is_enforced_after_stripping(self, reviewer: str) -> None:
        with pytest.raises(ValidationError):
            ApprovalDecision(decision="approve", reviewer=reviewer)

    def test_note_length_is_capped(self) -> None:
        decision = ApprovalDecision(decision="approve", reviewer="On-call", note="n" * 500)
        assert len(decision.note) == 500
        with pytest.raises(ValidationError):
            ApprovalDecision(decision="approve", reviewer="On-call", note="n" * 501)

    def test_decision_value_is_restricted(self) -> None:
        with pytest.raises(ValidationError):
            ApprovalDecision.model_validate({"decision": "maybe", "reviewer": "On-call"})

    def test_unknown_fields_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ApprovalDecision.model_validate(
                {"decision": "approve", "reviewer": "On-call", "force": True}
            )
