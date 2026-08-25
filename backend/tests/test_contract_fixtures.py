"""Cross-language contract guard.

`contract-fixtures/` is shared with the frontend Vitest suite. These tests prove the fixtures
still match what the engine produces, so a backend contract change cannot silently break the UI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.workflow.schemas import WorkflowRun

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "contract-fixtures"
FIXTURE_NAMES = ("awaiting-approval-run", "completed-run", "rejected-run")


def load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def shape(node: Any, path: str = "") -> set[str]:
    """Collect every key path so structural drift is detected regardless of values."""
    paths: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            current = f"{path}.{key}" if path else key
            paths.add(current)
            paths |= shape(value, current)
    elif isinstance(node, list) and node:
        paths |= shape(node[0], f"{path}[]")
    return paths


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_every_fixture_exists(name: str) -> None:
    assert (FIXTURE_DIR / f"{name}.json").is_file()


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixtures_validate_against_the_backend_contract(name: str) -> None:
    run = WorkflowRun.model_validate(load(name))

    assert run.id == "INC-FIXTURE"
    assert len(run.agents) == 17


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixtures_round_trip_without_losing_fields(name: str) -> None:
    payload = load(name)

    reserialized = WorkflowRun.model_validate(payload).model_dump(mode="json", by_alias=True)

    assert reserialized == payload


def test_the_awaiting_approval_fixture_is_paused_at_the_gate() -> None:
    payload = load("awaiting-approval-run")

    assert payload["status"] == "awaiting_approval"
    assert payload["approval"]["status"] == "pending"
    assert payload["verification"] is None
    assert all(event["type"] != "remediation" for event in payload["events"])


def test_the_completed_fixture_covers_the_resolved_path() -> None:
    payload = load("completed-run")

    assert payload["status"] == "completed"
    assert payload["verification"]["status"] == "passed"
    assert payload["outcome"]["followUps"]


def test_the_rejected_fixture_covers_the_stopped_path() -> None:
    payload = load("rejected-run")

    assert payload["status"] == "rejected"
    assert payload["outcome"] is None
    assert all(event["type"] != "remediation" for event in payload["events"])


async def test_fixtures_still_match_freshly_generated_runs(
    pending_run: WorkflowRun, completed_run: WorkflowRun
) -> None:
    """Regenerate with `python scripts/export_contract_fixtures.py` when this fails."""
    live_pending = pending_run.model_dump(mode="json", by_alias=True)
    live_completed = completed_run.model_dump(mode="json", by_alias=True)

    assert shape(live_pending) == shape(load("awaiting-approval-run"))
    assert shape(live_completed) == shape(load("completed-run"))
