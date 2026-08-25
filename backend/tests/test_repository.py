"""Storage semantics: validation, copy isolation, recency, and eviction."""

from __future__ import annotations

from app.workflow.repository import MAX_RETAINED_RUNS, WorkflowRepository, workflow_repository
from app.workflow.schemas import WorkflowRun


def with_id(run: WorkflowRun, run_id: str) -> WorkflowRun:
    return run.model_copy(deep=True, update={"id": run_id})


async def test_saved_run_can_be_read_back_unchanged(pending_run: WorkflowRun) -> None:
    repository = WorkflowRepository()
    saved = repository.save(pending_run)
    fetched = repository.get(pending_run.id)

    assert saved == pending_run
    assert fetched == pending_run


def test_unknown_ids_return_none() -> None:
    assert WorkflowRepository().get("INC-MISSING") is None


async def test_stored_state_is_isolated_from_the_caller(pending_run: WorkflowRun) -> None:
    repository = WorkflowRepository()
    repository.save(pending_run)

    pending_run.status = "failed"
    pending_run.agents[0].status = "failed"

    stored = repository.get(pending_run.id)
    assert stored is not None
    assert stored.status == "awaiting_approval"
    assert stored.agents[0].status != "failed"


async def test_returned_runs_are_defensive_copies(pending_run: WorkflowRun) -> None:
    repository = WorkflowRepository()
    repository.save(pending_run)

    first = repository.get(pending_run.id)
    assert first is not None
    first.status = "failed"
    first.events.clear()

    second = repository.get(pending_run.id)
    assert second is not None
    assert second.status == "awaiting_approval"
    assert len(second.events) == len(pending_run.events)


async def test_saving_the_same_id_replaces_the_previous_state(
    pending_run: WorkflowRun, completed_run: WorkflowRun
) -> None:
    repository = WorkflowRepository()
    repository.save(pending_run)
    repository.save(with_id(completed_run, pending_run.id))

    stored = repository.get(pending_run.id)
    assert stored is not None
    assert stored.status == "completed"


async def test_oldest_runs_are_evicted_beyond_the_retention_limit(
    pending_run: WorkflowRun,
) -> None:
    repository = WorkflowRepository(max_runs=3)
    for index in range(4):
        repository.save(with_id(pending_run, f"INC-{index}"))

    assert repository.get("INC-0") is None
    assert [repository.get(f"INC-{index}") is not None for index in range(1, 4)] == [True] * 3


async def test_resaving_a_run_refreshes_its_recency(pending_run: WorkflowRun) -> None:
    repository = WorkflowRepository(max_runs=2)
    repository.save(with_id(pending_run, "INC-A"))
    repository.save(with_id(pending_run, "INC-B"))

    repository.save(with_id(pending_run, "INC-A"))
    repository.save(with_id(pending_run, "INC-C"))

    assert repository.get("INC-A") is not None
    assert repository.get("INC-C") is not None
    assert repository.get("INC-B") is None


async def test_clear_removes_every_stored_run(pending_run: WorkflowRun) -> None:
    repository = WorkflowRepository()
    repository.save(pending_run)
    repository.clear()

    assert repository.get(pending_run.id) is None


def test_the_shared_repository_uses_the_documented_retention_limit() -> None:
    assert isinstance(workflow_repository, WorkflowRepository)
    assert MAX_RETAINED_RUNS == 50
