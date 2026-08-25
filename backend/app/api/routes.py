"""Workflow HTTP API.

Route handlers stay thin: validate, guard, delegate to the engine, persist, respond.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import ProviderDep, RepositoryDep
from app.workflow.engine import WorkflowStateError, decide_workflow, start_workflow
from app.workflow.schemas import ApiError, ApprovalDecision, IncidentInput, WorkflowRun
from app.workflow.security import contains_likely_secret

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    400: {"model": ApiError},
    404: {"model": ApiError},
    409: {"model": ApiError},
}


@router.post(
    "",
    response_model=WorkflowRun,
    status_code=status.HTTP_201_CREATED,
    responses=_ERROR_RESPONSES,
    summary="Start an incident workflow and run it to the approval boundary",
)
async def create_workflow(
    incident: IncidentInput,
    provider: ProviderDep,
    repository: RepositoryDep,
) -> WorkflowRun:
    if contains_likely_secret(incident.model_dump(mode="json")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Remove credentials or secret-like values before starting a workflow",
        )

    run = await start_workflow(incident, provider)
    return repository.save(run)


@router.get(
    "/{run_id}",
    response_model=WorkflowRun,
    responses=_ERROR_RESPONSES,
    summary="Fetch a previously created workflow run",
)
async def read_workflow(run_id: str, repository: RepositoryDep) -> WorkflowRun:
    run = repository.get(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow run not found",
        )
    return run


@router.post(
    "/{run_id}/decision",
    response_model=WorkflowRun,
    responses=_ERROR_RESPONSES,
    summary="Record the human approval decision and resume or stop the workflow",
)
async def decide(
    run_id: str,
    decision: ApprovalDecision,
    provider: ProviderDep,
    repository: RepositoryDep,
) -> WorkflowRun:
    current_run = repository.get(run_id)
    if current_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow run not found",
        )

    if contains_likely_secret(decision.model_dump(mode="json")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Remove credentials or secret-like values from the decision note",
        )

    try:
        run = await decide_workflow(current_run, decision, provider)
    except WorkflowStateError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return repository.save(run)
