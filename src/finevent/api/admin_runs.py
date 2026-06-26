"""Admin workflow run endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from finevent.api.errors import api_error
from finevent.api.job_runner import (
    RunQueueFullError,
    cancel_run,
    create_run,
    get_run,
    list_runs,
    read_run_logs,
    stream_run_logs,
)

router = APIRouter(prefix="/admin/runs", tags=["admin-runs"])


class CreateRunRequest(BaseModel):
    workflow_name: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)


@router.get("")
def list_admin_runs(
    status: str | None = Query(default=None),
    workflow_name: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return list_runs(status=status, workflow_name=workflow_name, limit=limit, offset=offset)


@router.post("")
def create_admin_run(payload: CreateRunRequest) -> dict[str, Any]:
    try:
        run_state = create_run(payload.workflow_name, payload.config)
    except ValueError as exc:
        message = str(exc)
        is_unknown_workflow = message.startswith("Unknown workflow_name")
        raise api_error(
            422,
            "UNKNOWN_WORKFLOW" if is_unknown_workflow else "INVALID_WORKFLOW_CONFIG",
            message,
            details={"workflow_name": payload.workflow_name},
        ) from exc
    except RunQueueFullError as exc:
        raise api_error(
            429,
            "RUN_QUEUE_FULL",
            str(exc),
        ) from exc
    return {
        "run": run_state.to_dict(),
        "run_id": run_state.run_id,
        "status": run_state.status,
        "detail_url": f"/admin/runs/{run_state.run_id}",
    }


@router.get("/{run_id}")
def get_admin_run(run_id: str) -> dict[str, Any]:
    run_state = get_run(run_id)
    if run_state is None:
        raise api_error(
            404,
            "RUN_NOT_FOUND",
            "Admin run does not exist.",
            details={"run_id": run_id},
        )
    return run_state.to_dict()


@router.post("/{run_id}/cancel")
def cancel_admin_run(run_id: str) -> dict[str, Any]:
    run_state = cancel_run(run_id)
    if run_state is None:
        raise api_error(
            404,
            "RUN_NOT_FOUND",
            "Admin run does not exist.",
            details={"run_id": run_id},
        )
    return run_state.to_dict()


@router.get("/{run_id}/logs")
def get_admin_run_logs(
    run_id: str,
    step_id: str | None = Query(default=None),
    level: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    if get_run(run_id) is None:
        raise api_error(
            404,
            "RUN_NOT_FOUND",
            "Admin run does not exist.",
            details={"run_id": run_id},
        )
    return read_run_logs(
        run_id,
        step_id=step_id,
        level=level,
        limit=limit,
        offset=offset,
    )


@router.get("/{run_id}/logs/stream")
def stream_admin_run_logs(run_id: str) -> StreamingResponse:
    if get_run(run_id) is None:
        raise api_error(
            404,
            "RUN_NOT_FOUND",
            "Admin run does not exist.",
            details={"run_id": run_id},
        )
    return StreamingResponse(stream_run_logs(run_id), media_type="text/event-stream")
