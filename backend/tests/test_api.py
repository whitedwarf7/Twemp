"""HTTP contract: status codes, camelCase payloads, error shape, CORS, and guards."""

from __future__ import annotations

import re
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import provider_dependency, repository_dependency
from app.main import app
from app.workflow.repository import WorkflowRepository
from app.workflow.schemas import DEFAULT_INCIDENT, WorkflowRun

ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
SNAKE_CASE_KEY = re.compile(r"_[a-z]")


def incident(**overrides: Any) -> dict[str, Any]:
    return {**DEFAULT_INCIDENT.model_dump(mode="json", by_alias=True), **overrides}


def create_run(client: TestClient) -> dict[str, Any]:
    response = client.post("/api/workflows", json=incident())
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body


def collect_keys(node: Any, keys: set[str]) -> set[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            keys.add(key)
            collect_keys(value, keys)
    elif isinstance(node, list):
        for item in node:
            collect_keys(item, keys)
    return keys


class TestSystemEndpoints:
    def test_health_reports_the_active_provider_mode(self, client: TestClient) -> None:
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "provider": "demo"}

    def test_the_openapi_document_describes_the_workflow_api(self, client: TestClient) -> None:
        schema = client.get("/openapi.json").json()

        assert "/api/workflows" in schema["paths"]
        assert "/api/workflows/{run_id}" in schema["paths"]
        assert "/api/workflows/{run_id}/decision" in schema["paths"]
        assert "post" in schema["paths"]["/api/workflows"]


class TestCreateWorkflow:
    def test_a_new_run_is_created_and_paused_for_approval(self, client: TestClient) -> None:
        body = create_run(client)

        assert body["status"] == "awaiting_approval"
        assert body["phase"] == "approval"
        assert body["mode"] == "demo"
        assert body["approval"]["status"] == "pending"
        assert body["verification"] is None
        assert body["outcome"] is None

    def test_the_payload_is_entirely_camel_case(self, client: TestClient) -> None:
        body = create_run(client)

        offenders = {key for key in collect_keys(body, set()) if SNAKE_CASE_KEY.search(key)}
        assert offenders == set()

    def test_the_payload_exposes_the_full_agent_hierarchy(self, client: TestClient) -> None:
        body = create_run(client)
        roles = [agent["role"] for agent in body["agents"]]

        assert body["metrics"]["agentsTotal"] == 17
        assert roles.count("main-orchestrator") == 1
        assert roles.count("sub-orchestrator") == 4
        assert roles.count("specialist") == 12
        assert len(body["findings"]) == 10
        assert len(body["teamReports"]) == 4

    def test_timestamps_use_the_iso_z_contract(self, client: TestClient) -> None:
        body = create_run(client)

        assert ISO_Z.match(body["startedAt"])
        assert ISO_Z.match(body["updatedAt"])
        assert ISO_Z.match(body["approval"]["requestedAt"])
        assert ISO_Z.match(body["events"][0]["timestamp"])

    def test_the_plan_is_returned_but_not_executed(self, client: TestClient) -> None:
        body = create_run(client)

        assert body["plan"]["riskLevel"] == "medium"
        assert body["plan"]["actions"][0]["ownerAgentId"] == "response-lead"
        assert all(action["reversible"] for action in body["plan"]["actions"])
        assert all(event["type"] != "remediation" for event in body["events"])

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("title", "no"),
            ("description", "too short"),
            ("service", "has space"),
            ("severity", "SEV-9"),
            ("region", "e"),
            ("signals", []),
            ("signals", ["ab"]),
        ],
        ids=["title", "description", "service", "severity", "region", "no-signals", "short-signal"],
    )
    def test_invalid_fields_are_rejected_with_details(
        self, client: TestClient, field: str, value: Any
    ) -> None:
        response = client.post("/api/workflows", json=incident(**{field: value}))
        body = response.json()

        assert response.status_code == 400
        assert body["error"] == "Request validation failed"
        assert any(field in detail for detail in body["details"])

    def test_unknown_fields_are_rejected(self, client: TestClient) -> None:
        response = client.post("/api/workflows", json=incident(runbook="delete-database"))

        assert response.status_code == 400
        assert any("runbook" in detail for detail in response.json()["details"])

    def test_a_malformed_body_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/api/workflows",
            content=b"{not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        assert response.json()["error"] == "Request validation failed"

    @pytest.mark.parametrize(
        "description",
        [
            "Retry storm after deploy. api_key=AKIA-super-secret-value-1234567890",
            "Router logs leaked sk-abcdefghijklmnopqrstuvwxyz during the incident window",
        ],
        ids=["assignment", "openai-key"],
    )
    def test_credential_shaped_content_is_blocked(
        self, client: TestClient, description: str
    ) -> None:
        response = client.post("/api/workflows", json=incident(description=description))

        assert response.status_code == 400
        assert "secret-like" in response.json()["error"]

    def test_a_blocked_request_is_never_stored(
        self, client: TestClient, repository: WorkflowRepository
    ) -> None:
        client.post("/api/workflows", json=incident(description="api_key=leaked-value-here-now"))

        assert repository.get("INC-ANY") is None


class TestReadWorkflow:
    def test_a_stored_run_is_returned(self, client: TestClient) -> None:
        created = create_run(client)

        response = client.get(f"/api/workflows/{created['id']}")

        assert response.status_code == 200
        assert response.json() == created

    def test_unknown_runs_return_not_found(self, client: TestClient) -> None:
        response = client.get("/api/workflows/INC-UNKNOWN")

        assert response.status_code == 404
        assert response.json() == {"error": "Workflow run not found"}


class TestDecisionEndpoint:
    def test_approval_resolves_the_incident(self, client: TestClient) -> None:
        created = create_run(client)

        response = client.post(
            f"/api/workflows/{created['id']}/decision",
            json={"decision": "approve", "reviewer": "Primary on-call", "note": "Reviewed"},
        )
        body = response.json()

        assert response.status_code == 200
        assert body["status"] == "completed"
        assert body["phase"] == "resolved"
        assert body["verification"]["status"] == "passed"
        assert len(body["outcome"]["followUps"]) >= 1
        assert body["approval"]["decidedBy"] == "Primary on-call"
        assert ISO_Z.match(body["approval"]["decidedAt"])

    def test_rejection_records_the_decision_without_remediation(self, client: TestClient) -> None:
        created = create_run(client)

        response = client.post(
            f"/api/workflows/{created['id']}/decision",
            json={"decision": "reject", "reviewer": "Incident commander", "note": "Too broad"},
        )
        body = response.json()

        assert response.status_code == 200
        assert body["status"] == "rejected"
        assert body["approval"]["status"] == "rejected"
        assert all(event["type"] != "remediation" for event in body["events"])

    def test_the_resolved_run_replaces_the_stored_state(self, client: TestClient) -> None:
        created = create_run(client)
        client.post(
            f"/api/workflows/{created['id']}/decision",
            json={"decision": "approve", "reviewer": "Primary on-call"},
        )

        stored = client.get(f"/api/workflows/{created['id']}").json()

        assert stored["status"] == "completed"

    def test_deciding_twice_is_a_conflict(self, client: TestClient) -> None:
        created = create_run(client)
        client.post(
            f"/api/workflows/{created['id']}/decision",
            json={"decision": "approve", "reviewer": "Primary on-call"},
        )

        replay = client.post(
            f"/api/workflows/{created['id']}/decision",
            json={"decision": "approve", "reviewer": "Primary on-call"},
        )

        assert replay.status_code == 409
        assert "not waiting for an approval decision" in replay.json()["error"]

    def test_decisions_for_unknown_runs_return_not_found(self, client: TestClient) -> None:
        response = client.post(
            "/api/workflows/INC-UNKNOWN/decision",
            json={"decision": "approve", "reviewer": "Primary on-call"},
        )

        assert response.status_code == 404
        assert response.json() == {"error": "Workflow run not found"}

    @pytest.mark.parametrize(
        "payload",
        [
            {"decision": "maybe", "reviewer": "Primary on-call"},
            {"decision": "approve", "reviewer": "x"},
            {"decision": "approve"},
            {"decision": "approve", "reviewer": "On-call", "note": "n" * 501},
            {"decision": "approve", "reviewer": "On-call", "force": True},
        ],
        ids=["bad-decision", "short-reviewer", "missing-reviewer", "long-note", "unknown-field"],
    )
    def test_invalid_decisions_are_rejected(
        self, client: TestClient, payload: dict[str, Any]
    ) -> None:
        created = create_run(client)

        response = client.post(f"/api/workflows/{created['id']}/decision", json=payload)

        assert response.status_code == 400
        assert response.json()["error"] == "Request validation failed"

    def test_a_rejected_decision_leaves_the_run_awaiting_approval(self, client: TestClient) -> None:
        created = create_run(client)

        client.post(
            f"/api/workflows/{created['id']}/decision",
            json={"decision": "approve", "reviewer": "x"},
        )

        assert client.get(f"/api/workflows/{created['id']}").json()["status"] == "awaiting_approval"

    def test_credential_shaped_notes_are_blocked(self, client: TestClient) -> None:
        created = create_run(client)

        response = client.post(
            f"/api/workflows/{created['id']}/decision",
            json={
                "decision": "approve",
                "reviewer": "Primary on-call",
                "note": "use api_key=super-secret-value to roll back",
            },
        )

        assert response.status_code == 400
        assert "secret-like" in response.json()["error"]
        assert client.get(f"/api/workflows/{created['id']}").json()["status"] == "awaiting_approval"


class TestCrossOriginPolicy:
    def test_the_configured_frontend_origin_is_allowed(self, client: TestClient) -> None:
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})

        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

    def test_preflight_advertises_only_the_supported_methods(self, client: TestClient) -> None:
        response = client.options(
            "/api/workflows",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        allowed = response.headers["access-control-allow-methods"]

        assert response.status_code == 200
        assert "POST" in allowed
        assert "DELETE" not in allowed

    def test_unlisted_origins_are_not_granted_access(self, client: TestClient) -> None:
        response = client.get("/health", headers={"Origin": "http://evil.test"})

        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers


class TestUnexpectedFailures:
    def test_internal_errors_return_a_generic_contract_error(
        self, repository: WorkflowRepository
    ) -> None:
        class BrokenRepository(WorkflowRepository):
            def get(self, run_id: str) -> WorkflowRun | None:
                raise RuntimeError("database connection lost")

        app.dependency_overrides[repository_dependency] = BrokenRepository
        try:
            with TestClient(app, raise_server_exceptions=False) as broken_client:
                response = broken_client.get("/api/workflows/INC-ANY")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 500
        assert response.json() == {"error": "The workflow request could not be completed"}

    def test_provider_outages_are_reported_as_a_failed_run(
        self, repository: WorkflowRepository
    ) -> None:
        from app.workflow.demo_provider import DemoAgentProvider
        from app.workflow.provider import SpecialistTask
        from app.workflow.schemas import AgentFinding

        class OutageProvider(DemoAgentProvider):
            async def run_specialist(self, task: SpecialistTask) -> AgentFinding:
                raise RuntimeError("provider unavailable")

        app.dependency_overrides[provider_dependency] = OutageProvider
        app.dependency_overrides[repository_dependency] = lambda: repository
        try:
            with TestClient(app) as outage_client:
                response = outage_client.post("/api/workflows", json=incident())
        finally:
            app.dependency_overrides.clear()

        body = response.json()
        assert response.status_code == 201
        assert body["status"] == "failed"
        assert body["plan"] is None
        assert all(event["type"] != "remediation" for event in body["events"])
