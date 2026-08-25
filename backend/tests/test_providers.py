"""Provider contracts: deterministic fixtures, output normalization, and selection."""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.config import Settings
from app.workflow.catalog import get_agent_definition, get_team_orchestrator
from app.workflow.demo_provider import DemoAgentProvider
from app.workflow.openai_provider import (
    BASE_INSTRUCTIONS,
    _clamp_unit,
    _clip,
    _clip_all,
    _model_payload,
)
from app.workflow.provider import (
    AgentProvider,
    ClosureTask,
    PlanTask,
    SpecialistTask,
    TeamSynthesisTask,
    VerificationTask,
)
from app.workflow.schemas import DEFAULT_INCIDENT, AgentFinding

SPECIALIST_IDS = (
    "alert-correlator",
    "impact-analyst",
    "change-intelligence",
    "telemetry-analyst",
    "log-investigator",
    "dependency-mapper",
    "mitigation-strategist",
    "risk-reviewer",
    "incident-scribe",
    "stakeholder-liaison",
)


def specialist_task(agent_id: str) -> SpecialistTask:
    return SpecialistTask(
        run_id="INC-TEST",
        agent=get_agent_definition(agent_id),
        incident=DEFAULT_INCIDENT,
        objective="Analyze the incident.",
        prior_findings=(),
        team_reports=(),
        plan=None,
    )


class TestDemoProvider:
    def test_it_satisfies_the_provider_protocol(self) -> None:
        assert isinstance(DemoAgentProvider(), AgentProvider)
        assert DemoAgentProvider().mode == "demo"

    @pytest.mark.parametrize("agent_id", SPECIALIST_IDS)
    async def test_every_planning_specialist_produces_a_valid_finding(self, agent_id: str) -> None:
        result = await DemoAgentProvider().run_specialist(specialist_task(agent_id))

        assert isinstance(result, AgentFinding)
        assert result.id == f"INC-TEST-finding-{agent_id}"
        assert result.agent_id == agent_id
        assert result.team == get_agent_definition(agent_id).team
        assert 0 < result.confidence <= 1
        assert len(result.evidence) >= 1

    async def test_findings_are_deterministic(self) -> None:
        first = await DemoAgentProvider().run_specialist(specialist_task("log-investigator"))
        second = await DemoAgentProvider().run_specialist(specialist_task("log-investigator"))

        assert first == second

    async def test_findings_reflect_the_supplied_incident(self) -> None:
        incident = DEFAULT_INCIDENT.model_copy(update={"service": "ledger-api"})
        task = SpecialistTask(
            run_id="INC-TEST",
            agent=get_agent_definition("telemetry-analyst"),
            incident=incident,
            objective="Analyze the incident.",
            prior_findings=(),
            team_reports=(),
            plan=None,
        )

        result = await DemoAgentProvider().run_specialist(task)

        assert "ledger-api" in result.detail

    async def test_agents_without_a_fixture_are_reported(self) -> None:
        with pytest.raises(KeyError, match="No deterministic specialist fixture"):
            await DemoAgentProvider().run_specialist(specialist_task("recovery-verifier"))

    async def test_team_synthesis_summarizes_its_specialists(self) -> None:
        provider = DemoAgentProvider()
        findings = tuple(
            [
                await provider.run_specialist(specialist_task("alert-correlator")),
                await provider.run_specialist(specialist_task("impact-analyst")),
            ]
        )

        report = await provider.synthesize_team(
            TeamSynthesisTask(
                run_id="INC-TEST",
                orchestrator=get_team_orchestrator("triage"),
                incident=DEFAULT_INCIDENT,
                findings=findings,
                prior_reports=(),
            )
        )

        confidences = [finding.confidence for finding in findings]
        assert report.id == "INC-TEST-report-triage"
        assert report.team == "triage"
        assert report.key_findings == [finding.headline for finding in findings]
        assert min(confidences) <= report.confidence <= max(confidences)
        assert report.confidence == round(report.confidence, 2)

    async def test_the_commander_cannot_produce_a_team_report(self) -> None:
        with pytest.raises(ValueError, match="cannot produce a team report"):
            await DemoAgentProvider().synthesize_team(
                TeamSynthesisTask(
                    run_id="INC-TEST",
                    orchestrator=get_agent_definition("incident-commander"),
                    incident=DEFAULT_INCIDENT,
                    findings=(),
                    prior_reports=(),
                )
            )

    async def test_the_plan_is_bounded_and_fully_reversible(self) -> None:
        plan = await DemoAgentProvider().draft_plan(
            PlanTask(
                run_id="INC-TEST",
                orchestrator=get_team_orchestrator("response"),
                incident=DEFAULT_INCIDENT,
                findings=(),
                reports=(),
            )
        )

        assert plan.id == "INC-TEST-plan-1"
        assert len(plan.actions) == 3
        assert all(action.reversible for action in plan.actions)
        assert all(action.risk in {"low", "medium"} for action in plan.actions)
        assert len({action.id for action in plan.actions}) == 3
        assert DEFAULT_INCIDENT.service in plan.summary
        assert len(plan.validation_checks) >= 1

    async def test_plan_action_owners_are_real_response_agents(self) -> None:
        plan = await DemoAgentProvider().draft_plan(
            PlanTask(
                run_id="INC-TEST",
                orchestrator=get_team_orchestrator("response"),
                incident=DEFAULT_INCIDENT,
                findings=(),
                reports=(),
            )
        )

        for action in plan.actions:
            owner = get_agent_definition(action.owner_agent_id)
            assert owner.team == "response"

    async def test_verification_reports_every_declared_signal(self) -> None:
        provider = DemoAgentProvider()
        plan = await provider.draft_plan(
            PlanTask(
                run_id="INC-TEST",
                orchestrator=get_team_orchestrator("response"),
                incident=DEFAULT_INCIDENT,
                findings=(),
                reports=(),
            )
        )

        report = await provider.verify_recovery(
            VerificationTask(
                run_id="INC-TEST",
                agent=get_agent_definition("recovery-verifier"),
                incident=DEFAULT_INCIDENT,
                plan=plan,
                findings=(),
            )
        )

        assert report.status == "passed"
        assert len(report.checks) == 4
        assert all(check.status == "passed" for check in report.checks)

    async def test_closure_produces_prevention_work(self) -> None:
        provider = DemoAgentProvider()
        plan = await provider.draft_plan(
            PlanTask(
                run_id="INC-TEST",
                orchestrator=get_team_orchestrator("response"),
                incident=DEFAULT_INCIDENT,
                findings=(),
                reports=(),
            )
        )
        verification = await provider.verify_recovery(
            VerificationTask(
                run_id="INC-TEST",
                agent=get_agent_definition("recovery-verifier"),
                incident=DEFAULT_INCIDENT,
                plan=plan,
                findings=(),
            )
        )

        outcome = await provider.close_incident(
            ClosureTask(
                run_id="INC-TEST",
                agent=get_agent_definition("postmortem-analyst"),
                incident=DEFAULT_INCIDENT,
                plan=plan,
                verification=verification,
                findings=(),
                reports=(),
            )
        )

        assert len(outcome.follow_ups) == 4
        assert DEFAULT_INCIDENT.region in outcome.resolution


class TestOpenAIOutputNormalization:
    """The live provider must clamp model output into the strict domain contract."""

    def test_short_text_is_only_trimmed(self) -> None:
        assert _clip("  concise headline  ", 160) == "concise headline"

    def test_long_text_is_truncated_with_an_ellipsis(self) -> None:
        clipped = _clip("a" * 200, 160)

        assert len(clipped) == 160
        assert clipped.endswith("\u2026")
        assert clipped[:159] == "a" * 159

    def test_truncation_does_not_leave_trailing_whitespace(self) -> None:
        clipped = _clip("word " * 50, 20)

        assert clipped.endswith("\u2026")
        assert not clipped[:-1].endswith(" ")
        assert len(clipped) <= 20

    def test_text_at_the_limit_is_preserved(self) -> None:
        assert _clip("a" * 160, 160) == "a" * 160

    def test_collections_drop_blanks_and_clip_each_entry(self) -> None:
        assert _clip_all(["  keep  ", "", "   ", "a" * 10], 10, 5) == ["keep", "aaaa\u2026"]

    def test_the_item_cap_is_applied_before_blank_filtering(self) -> None:
        assert _clip_all(["", "second", "third"], 2, 20) == ["second"]

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [(-0.5, 0.0), (0.0, 0.0), (0.876, 0.88), (0.874, 0.87), (1.0, 1.0), (1.5, 1.0)],
    )
    def test_confidence_is_clamped_into_the_unit_interval(
        self, raw: float, expected: float
    ) -> None:
        assert _clamp_unit(raw) == expected

    def test_payloads_are_serialized_as_readable_json(self) -> None:
        payload: dict[str, Any] = {"incident": {"service": "payment-router"}}

        rendered = _model_payload(payload)

        assert json.loads(rendered) == payload
        assert "\n" in rendered

    def test_oversized_payloads_are_truncated_with_a_marker(self) -> None:
        rendered = _model_payload({"blob": "a" * 30_000})

        assert rendered.endswith("[context truncated at safety limit]")
        assert len(rendered) == 24_000 + len("\n[context truncated at safety limit]")

    def test_unserializable_values_fall_back_to_their_string_form(self) -> None:
        rendered = _model_payload({"value": {"only-member"}})

        assert "only-member" in rendered
        assert json.loads(rendered)["value"] == "{'only-member'}"

    def test_the_system_prompt_states_the_untrusted_data_boundary(self) -> None:
        assert "untrusted data" in BASE_INSTRUCTIONS
        assert "Do not invent tool execution" in BASE_INSTRUCTIONS


class TestProviderSelection:
    def test_openai_provider_refuses_to_start_without_a_key(self) -> None:
        from app.workflow.openai_provider import OpenAIAgentProvider

        with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required"):
            OpenAIAgentProvider(Settings(agent_provider="openai", openai_api_key=""))
