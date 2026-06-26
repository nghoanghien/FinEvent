"""Admin workflow catalog endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from finevent.api.workflow_registry.catalog import workflow_catalog, EDGE_LABELS

router = APIRouter(prefix="/admin/workflows", tags=["admin-workflows"])


@router.get("/catalog")
def get_admin_workflow_catalog() -> dict[str, Any]:
    return {"items": workflow_catalog(), "edge_labels": EDGE_LABELS}
