"""Deterministic provider used for local development, tests, and credential-free demos."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from app.workflow.provider import (
    ClosureTask,
    PlanTask,
    SpecialistTask,
    TeamSynthesisTask,
    VerificationTask,
)
from app.workflow.schemas import (
    AgentFinding,
    FindingSeverity,
    IncidentOutcome,
    ProviderMode,
    RemediationAction,
    RemediationPlan,
    TeamReport,
    VerificationCheck,
    VerificationReport,
)


@dataclass(frozen=True)
class _FindingSeed:
    headline: str
    detail: Callable[[SpecialistTask], str]
    evidence: Callable[[SpecialistTask], list[str]]
    confidence: float
    severity: FindingSeverity


def _signal(task: SpecialistTask, index: int, fallback: str) -> str:
    signals = task.incident.signals
    return signals[index] if index < len(signals) else fallback


_FINDING_SEEDS: dict[str, _FindingSeed] = {
    "alert-correlator": _FindingSeed(
        headline="Three alert families share a single onset window",
        detail=lambda task: (
            f"Latency, HTTP error, and queue-depth alerts for {task.incident.service} all changed "
            "within the same two-minute window, indicating one incident rather than independent "
            "failures."
        ),
        evidence=lambda task: [
            f"First sustained breach observed in {task.incident.region}",
            _signal(task, 0, "Latency signal breached its threshold"),
            _signal(task, 1, "Error rate exceeded its threshold"),
        ],
        confidence=0.96,
        severity="critical",
    ),
    "impact-analyst": _FindingSeed(
        headline="Customer checkout completion is materially degraded",
        detail=lambda task: (
            f"The {task.incident.region} checkout path is the primary affected journey. Elevated "
            "latency and retries imply both failed purchases and duplicate-attempt risk, "
            f"supporting {task.incident.severity} handling."
        ),
        evidence=lambda task: [
            f"Scope is concentrated in {task.incident.region}",
            "Estimated checkout completion is 31% below the normal band",
            "Other regions remain inside their error-budget burn thresholds",
        ],
        confidence=0.91,
        severity="critical",
    ),
    "change-intelligence": _FindingSeed(
        headline="Incident onset strongly correlates with the latest router release",
        detail=lambda task: (
            f"Release 2026.08.25.3 of {task.incident.service} reached {task.incident.region} six "
            "minutes before the first alert. No concurrent database or gateway configuration "
            "change was recorded."
        ),
        evidence=lambda _task: [
            "Release 2026.08.25.3 completed at 14:26 UTC",
            "First alert fired at 14:32 UTC",
            "Previous release has a known-good 24-hour baseline",
        ],
        confidence=0.94,
        severity="warning",
    ),
    "telemetry-analyst": _FindingSeed(
        headline="Connection-pool saturation is driving latency amplification",
        detail=lambda task: (
            f"{task.incident.service} instances in {task.incident.region} show pool utilization "
            "pinned above 97% while CPU and memory remain normal. Retry amplification explains "
            "the rising queue depth."
        ),
        evidence=lambda _task: [
            "Gateway connection pool: 97-100% utilized",
            "Application CPU: 41%; memory: 58%",
            "Retry attempts per checkout increased from 1.1 to 3.8",
        ],
        confidence=0.93,
        severity="critical",
    ),
    "log-investigator": _FindingSeed(
        headline="New routing branch leaks gateway connections on timeout",
        detail=lambda task: (
            f"Logs from {task.incident.service} repeatedly pair upstream timeout messages with "
            "missing connection-release markers on the new v3 routing branch. The legacy branch "
            "closes connections correctly."
        ),
        evidence=lambda _task: [
            "PAYMENT_UPSTREAM_TIMEOUT increased 22x after deployment",
            "releaseConnection marker absent on the v3 timeout path",
            "Legacy v2 path retains a balanced acquire/release ratio",
        ],
        confidence=0.95,
        severity="critical",
    ),
    "dependency-mapper": _FindingSeed(
        headline="External payment gateway is healthy; failure is at the client boundary",
        detail=lambda task: (
            "The upstream gateway, checkout API, and database are healthy outside calls made by "
            f"{task.incident.service}. The fault boundary is the router's connection lifecycle in "
            f"{task.incident.region}."
        ),
        evidence=lambda _task: [
            "Gateway synthetic probes remain below 180 ms",
            "Database query p95 remains below 24 ms",
            "Only v3 router instances show elevated open connections",
        ],
        confidence=0.92,
        severity="warning",
    ),
    "mitigation-strategist": _FindingSeed(
        headline="A regional rollback is the fastest bounded mitigation",
        detail=lambda task: (
            f"Rolling {task.incident.service} in {task.incident.region} back to the previous "
            "release removes the suspected path while containing change to the affected region. "
            "Queue recovery should wait for latency stabilization."
        ),
        evidence=lambda _task: [
            "Previous release artifact passed current smoke tests",
            "Regional deployment supports one-click rollback",
            "Traffic shifting alone would move retry pressure downstream",
        ],
        confidence=0.90,
        severity="warning",
    ),
    "risk-reviewer": _FindingSeed(
        headline="Rollback risk is lower than continued customer impact",
        detail=lambda _task: (
            "The previous release is schema-compatible and the rollout can be stopped after the "
            "first canary. The main secondary risk is replaying the payment retry queue too "
            "quickly."
        ),
        evidence=lambda _task: [
            "No database migration accompanied the release",
            "Rollback canary limits initial exposure to 5% of instances",
            "Queue drain supports a configurable transactions-per-second cap",
        ],
        confidence=0.89,
        severity="warning",
    ),
    "incident-scribe": _FindingSeed(
        headline="Incident timeline and decision ledger are synchronized",
        detail=lambda task: (
            "The live record now captures alert onset, "
            f"{task.incident.service} deployment timing, hypotheses, evidence, and the approval "
            "boundary. Unverified claims are labeled as hypotheses."
        ),
        evidence=lambda _task: [
            "14:26 UTC - release completed",
            "14:32 UTC - first sustained SLO breach",
            "14:38 UTC - incident command workflow activated",
        ],
        confidence=0.98,
        severity="info",
    ),
    "stakeholder-liaison": _FindingSeed(
        headline="Stakeholder update is ready for release",
        detail=lambda task: (
            "Draft: We are investigating elevated checkout latency in "
            f"{task.incident.region}. The team has isolated the issue and prepared a bounded "
            "mitigation. No remediation will run before human approval."
        ),
        evidence=lambda _task: [
            "Message states confirmed customer impact only",
            "No speculative root cause is presented as fact",
            "Next update target is 20 minutes",
        ],
        confidence=0.97,
        severity="info",
    ),
}

_TEAM_COPY: dict[str, tuple[str, str]] = {
    "triage": (
        "Scope confirmed; focused incident response is warranted",
        "Prioritize the affected regional release path and preserve the current alert and "
        "deployment evidence.",
    ),
    "investigation": (
        "Evidence converges on a connection lifecycle regression",
        "Treat the v3 timeout branch as the leading cause and prefer a reversible regional "
        "rollback over broad infrastructure changes.",
    ),
    "response": (
        "Reversible mitigation path prepared",
        "Canary the previous release, expand only on healthy signals, then drain the retry queue "
        "at a capped rate.",
    ),
    "communications": (
        "Incident record and stakeholder narrative are current",
        "Publish the impact-focused update now and issue a recovery update only after independent "
        "verification passes.",
    ),
}


class DemoAgentProvider:
    """Returns stable, schema-valid fixtures so the workflow is reproducible offline."""

    def __init__(self, latency_seconds: float = 0.0) -> None:
        self._latency_seconds = latency_seconds

    @property
    def mode(self) -> ProviderMode:
        return "demo"

    async def _pause(self) -> None:
        if self._latency_seconds > 0:
            await asyncio.sleep(self._latency_seconds)

    async def run_specialist(self, task: SpecialistTask) -> AgentFinding:
        await self._pause()
        seed = _FINDING_SEEDS.get(task.agent.id)
        if seed is None:
            raise KeyError(f"No deterministic specialist fixture for {task.agent.id}")

        return AgentFinding(
            id=f"{task.run_id}-finding-{task.agent.id}",
            agent_id=task.agent.id,
            team=task.agent.team,
            headline=seed.headline,
            detail=seed.detail(task),
            evidence=seed.evidence(task),
            confidence=seed.confidence,
            severity=seed.severity,
        )

    async def synthesize_team(self, task: TeamSynthesisTask) -> TeamReport:
        await self._pause()
        if task.orchestrator.team == "command":
            raise ValueError("The main orchestrator cannot produce a team report")

        title, recommendation = _TEAM_COPY[task.orchestrator.team]
        confidence = sum(finding.confidence for finding in task.findings) / max(
            len(task.findings), 1
        )

        return TeamReport(
            id=f"{task.run_id}-report-{task.orchestrator.team}",
            orchestrator_id=task.orchestrator.id,
            team=task.orchestrator.team,
            title=title,
            summary=" ".join(finding.headline for finding in task.findings),
            key_findings=[finding.headline for finding in task.findings],
            recommendation=recommendation,
            confidence=round(confidence, 2),
        )

    async def draft_plan(self, task: PlanTask) -> RemediationPlan:
        await self._pause()
        return RemediationPlan(
            id=f"{task.run_id}-plan-1",
            hypothesis=(
                "Release 2026.08.25.3 introduced a missing connection-release path after upstream "
                "timeouts, saturating the regional gateway pool and amplifying retries."
            ),
            summary=(
                f"Canary a rollback of {task.incident.service} in {task.incident.region}, expand "
                "only after golden signals recover, then drain queued retries at a controlled "
                "rate."
            ),
            risk_level="medium",
            blast_radius=(
                f"Only {task.incident.service} instances in {task.incident.region}; start with a "
                "5% canary."
            ),
            actions=[
                RemediationAction(
                    id="action-freeze",
                    title="Freeze regional changes and preserve evidence",
                    detail=(
                        "Pause unrelated deployments in the affected region and capture current "
                        "release, metric, and error-pattern references."
                    ),
                    owner_agent_id="response-lead",
                    risk="low",
                    reversible=True,
                    expected_signal="No additional configuration drift during mitigation",
                ),
                RemediationAction(
                    id="action-rollback",
                    title="Canary rollback to release 2026.08.24.7",
                    detail=(
                        "Roll back 5% of regional instances, observe for five minutes, and expand "
                        "only if latency and pool saturation improve."
                    ),
                    owner_agent_id="mitigation-strategist",
                    risk="medium",
                    reversible=True,
                    expected_signal="p95 latency below 800 ms and pool utilization below 70%",
                ),
                RemediationAction(
                    id="action-queue",
                    title="Drain the payment retry queue",
                    detail=(
                        "After service metrics stabilize, replay queued work at 20% of normal "
                        "throughput with duplicate-payment protection enabled."
                    ),
                    owner_agent_id="risk-reviewer",
                    risk="medium",
                    reversible=True,
                    expected_signal=(
                        "Queue depth declines without renewed latency or duplicate attempts"
                    ),
                ),
            ],
            rollback=(
                "Stop expansion immediately if canary error rate exceeds 2%, restore release "
                "2026.08.25.3, and isolate the region behind the existing traffic-shift control."
            ),
            validation_checks=[
                "Checkout p95 latency remains below 800 ms for ten minutes",
                "HTTP 5xx rate remains below 1%",
                "Connection-pool utilization remains below 70%",
                "Retry queue declines monotonically without duplicate-payment alerts",
            ],
        )

    async def verify_recovery(self, task: VerificationTask) -> VerificationReport:
        await self._pause()
        return VerificationReport(
            status="passed",
            summary=(
                f"All predeclared recovery checks passed for {task.incident.service} in "
                f"{task.incident.region}; service is stable enough to resolve the incident."
            ),
            checks=[
                VerificationCheck(
                    label="Checkout p95 latency",
                    value="612 ms",
                    status="passed",
                    detail="Below the 800 ms threshold for the full verification window",
                ),
                VerificationCheck(
                    label="HTTP 5xx rate",
                    value="0.4%",
                    status="passed",
                    detail="Returned to the normal operating band",
                ),
                VerificationCheck(
                    label="Connection pool",
                    value="54%",
                    status="passed",
                    detail="Stable with balanced acquire and release counts",
                ),
                VerificationCheck(
                    label="Retry queue",
                    value="-71%",
                    status="passed",
                    detail="Declining at the capped replay rate with no duplicate alerts",
                ),
            ],
        )

    async def close_incident(self, task: ClosureTask) -> IncidentOutcome:
        await self._pause()
        return IncidentOutcome(
            root_cause=(
                "A regression in the v3 payment routing timeout branch failed to release gateway "
                "connections, exhausting the regional pool and triggering retry amplification."
            ),
            resolution=(
                f"The team rolled {task.incident.service} in {task.incident.region} back to the "
                "previous release, verified recovery, and drained queued retries at a capped rate."
            ),
            customer_impact=(
                "EU checkout attempts experienced elevated latency and an estimated 31% reduction "
                "in successful completion during the incident window; no duplicate charges were "
                "detected."
            ),
            follow_ups=[
                "Add a connection-balance invariant test for every timeout branch",
                "Gate regional rollout on pool-saturation and retry-amplification canaries",
                "Add automatic duplicate-payment checks to queue replay procedures",
                "Complete a blameless review within two business days",
            ],
        )
