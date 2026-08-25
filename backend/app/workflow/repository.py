"""Bounded in-memory run store.

Suitable for the reference app only; production deployments need durable, transactional storage.
"""

from __future__ import annotations

import threading
from collections import OrderedDict

from app.workflow.schemas import WorkflowRun

MAX_RETAINED_RUNS = 50


class WorkflowRepository:
    def __init__(self, max_runs: int = MAX_RETAINED_RUNS) -> None:
        self._runs: OrderedDict[str, WorkflowRun] = OrderedDict()
        self._max_runs = max_runs
        self._lock = threading.Lock()

    def save(self, run: WorkflowRun) -> WorkflowRun:
        validated = WorkflowRun.model_validate(run.model_dump(by_alias=False))
        with self._lock:
            self._runs[validated.id] = validated.model_copy(deep=True)
            self._runs.move_to_end(validated.id)
            while len(self._runs) > self._max_runs:
                self._runs.popitem(last=False)
        return validated

    def get(self, run_id: str) -> WorkflowRun | None:
        with self._lock:
            run = self._runs.get(run_id)
            return run.model_copy(deep=True) if run is not None else None

    def clear(self) -> None:
        with self._lock:
            self._runs.clear()


workflow_repository = WorkflowRepository()
